"""Interview session state machine.

Tracks conversation history, current schema state, and delegates
extraction and policy decisions to the AI extractor and policy engine.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from backend.ai.extractor import LLMClient, StubLLMClient, extract_and_apply
from backend.interview.questions import completion_message, welcome_message
from backend.policy.engine import PolicyDecision, select_next_question
from backend.schema.canonical import CanonicalPlanSchema
from backend.schema.patch_ops import PatchOp, PatchResult, apply_patches
from backend.schema.provenance import ProvenanceField


class InterviewMessage(BaseModel):
    """A single message in the interview conversation."""

    role: str
    content: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class InterviewTurnResult(BaseModel):
    """Result of processing a single user message in the interview."""

    assistant_message: str
    patch_result: PatchResult | None = None
    policy_decision: PolicyDecision
    interview_complete: bool = False


_NAME_PREFIX_RE = re.compile(r"^(?:my name is|i am|i'm)\s+", flags=re.IGNORECASE)
_NAME_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z'-]*$")
_BIRTH_YEAR_RE = re.compile(r"\b(\d{4})\b")
_WORD_TEXT_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,49}$")
_NUMBER_RE = re.compile(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?")
_RANGE_RE = re.compile(r"(\d{2})\D+(\d{2})")
_AFFIRMATIVE_REPLIES = {"y", "yes", "yeah", "yep", "correct", "right", "that is right"}
_MIN_BIRTH_YEAR = 1900
_MAX_REASONABLE_AGE = 110


def _extract_full_name_fallback(user_message: str) -> str | None:
    """Best-effort fallback for obvious full-name replies.

    This only handles clear two-to-four token names and avoids numeric or
    punctuation-heavy messages.
    """
    normalized = " ".join(user_message.strip().split())
    if not normalized:
        return None

    normalized = _NAME_PREFIX_RE.sub("", normalized).strip(" .,!?:;")
    if not normalized:
        return None
    if any(ch.isdigit() for ch in normalized):
        return None

    parts = normalized.split(" ")
    if len(parts) < 2 or len(parts) > 4:
        return None
    if not all(_NAME_TOKEN_RE.match(part) for part in parts):
        return None

    return " ".join(part.capitalize() for part in parts)


def _extract_birth_year_fallback(user_message: str) -> int | None:
    """Extract a likely birth year from free text when clearly provided."""
    match = _BIRTH_YEAR_RE.search(user_message)
    if not match:
        return None

    year = int(match.group(1))
    current_year = datetime.now(timezone.utc).year
    if year < _MIN_BIRTH_YEAR or year > current_year:
        return None
    if current_year - year > _MAX_REASONABLE_AGE:
        return None
    return year


def _merge_patch_results(
    primary: PatchResult, secondary: PatchResult
) -> PatchResult:
    return PatchResult(
        applied=[*primary.applied, *secondary.applied],
        rejected=[*primary.rejected, *secondary.rejected],
        schema_snapshot_id=secondary.schema_snapshot_id,
        warnings=[*primary.warnings, *secondary.warnings],
    )


def _parse_number(user_message: str) -> float | None:
    match = _NUMBER_RE.search(user_message.replace("$", ""))
    if not match:
        return None
    return float(match.group(0).replace(",", ""))


def _parse_money(user_message: str) -> float | None:
    amount = _parse_number(user_message)
    if amount is None or amount < 0:
        return None
    return amount


def _parse_percent_as_ratio(user_message: str) -> float | None:
    value = _parse_number(user_message)
    if value is None:
        return None
    if "%" in user_message or value > 1.0:
        if value > 100:
            return None
        return value / 100.0
    if 0 <= value <= 1:
        return value
    return None


def _parse_percent_raw(user_message: str) -> float | None:
    """Parse percentage as raw number (e.g., '6%' -> 6.0, '3' -> 3.0)."""
    value = _parse_number(user_message)
    if value is None:
        return None
    # Strip % sign - we want the raw number
    if value > 100:
        return None
    if value < 0:
        return None
    return value


def _parse_word_text(user_message: str) -> str | None:
    normalized = " ".join(user_message.strip().split())
    if not normalized:
        return None
    if not _WORD_TEXT_RE.match(normalized):
        return None
    return normalized


def _parse_retirement_window(user_message: str) -> dict[str, float] | None:
    msg = user_message.strip()
    match = _RANGE_RE.search(msg)
    if match:
        lo = int(match.group(1))
        hi = int(match.group(2))
        if 40 <= lo <= 80 and 40 <= hi <= 80 and lo <= hi:
            return {"min": float(lo), "max": float(hi)}
        return None
    single = _parse_number(msg)
    if single is None:
        return None
    age = int(single)
    if 40 <= age <= 80:
        return {"min": float(age), "max": float(age)}
    return None


def _fallback_patch_for_target(
    target_field: str | None, user_message: str
) -> PatchOp | None:
    if target_field == "client.name":
        fallback_name = _extract_full_name_fallback(user_message)
        if fallback_name:
            return PatchOp(
                op="set",
                path="client.name",
                value=fallback_name,
                confidence=0.75,
            )
        return None

    if target_field == "client.birth_year":
        fallback_birth_year = _extract_birth_year_fallback(user_message)
        if fallback_birth_year is not None:
            return PatchOp(
                op="set",
                path="client.birth_year",
                value=fallback_birth_year,
                confidence=0.85,
            )
        return None

    if target_field in {"location.state", "location.city", "accounts.investment_strategy_id"}:
        text = _parse_word_text(user_message)
        if text:
            return PatchOp(op="set", path=target_field, value=text, confidence=0.8)
        return None

    if target_field == "housing.status":
        normalized = user_message.strip().lower()
        if normalized in {"rent", "renter", "renting"}:
            return PatchOp(op="set", path=target_field, value="rent", confidence=0.9)
        if normalized in {"own", "owner", "owning"}:
            return PatchOp(op="set", path=target_field, value="own", confidence=0.9)
        return None

    if target_field == "accounts.has_employer_plan":
        normalized = user_message.strip().lower()
        if normalized in {"yes", "y", "yeah", "yep", "yup", "sure", "correct", "true"}:
            return PatchOp(op="set", path=target_field, value=True, confidence=0.95)
        if normalized in {"no", "n", "nope", "nah", "false", "none"}:
            return PatchOp(op="set", path=target_field, value=False, confidence=0.95)
        return None

    if target_field == "client.retirement_window":
        window = _parse_retirement_window(user_message)
        if window:
            return PatchOp(op="set", path=target_field, value=window, confidence=0.85)
        return None

    if target_field in {
        "income.current_gross_annual",
        "retirement_philosophy.legacy_goal_total_real",
        "accounts.retirement_balance",
        "spending.retirement_monthly_real",
        "social_security.combined_at_67_monthly",
        "social_security.combined_at_70_monthly",
        "monte_carlo.legacy_floor",
    }:
        amount = _parse_money(user_message)
        if amount is not None:
            return PatchOp(op="set", path=target_field, value=amount, confidence=0.85)
        return None

    if target_field in {
        "retirement_philosophy.success_probability_target",
        "monte_carlo.required_success_rate",
        "accounts.savings_rate_percent",
    }:
        ratio = _parse_percent_as_ratio(user_message)
        if ratio is not None:
            return PatchOp(op="set", path=target_field, value=ratio, confidence=0.85)
        return None

    if target_field in {
        "accounts.employer_match_percent",
        "accounts.employee_contribution_percent",
    }:
        # These are stored as raw percentages (e.g., 6 for 6%), not ratios
        pct = _parse_percent_raw(user_message)
        if pct is not None:
            return PatchOp(op="set", path=target_field, value=pct, confidence=0.85)
        return None

    if target_field in {"monte_carlo.horizon_age", "social_security.claiming_preference"}:
        number = _parse_number(user_message)
        if number is None:
            return None
        ivalue = int(number)
        if target_field == "social_security.claiming_preference" and not (62 <= ivalue <= 70):
            return None
        if target_field == "monte_carlo.horizon_age" and not (80 <= ivalue <= 120):
            return None
        return PatchOp(op="set", path=target_field, value=ivalue, confidence=0.85)

    return None


def _invalid_input_feedback(
    target_field: str | None, user_message: str
) -> str | None:
    text = user_message.strip()
    if not target_field or not text:
        return None

    if target_field == "client.name":
        if len(text.split()) < 2:
            return (
                "Thanks — I need your full name (first and last) so I can match records "
                "correctly. For example: \"Bob Jones.\""
            )
        return "I couldn't quite read that as a full name. Please share first and last name."

    if target_field == "client.birth_year":
        current_year = datetime.now(timezone.utc).year
        year_match = _BIRTH_YEAR_RE.search(text)
        if year_match:
            year = int(year_match.group(1))
            if year > current_year:
                return (
                    f"{year} looks like a future year. Please share your actual birth year "
                    f"(for example, 1982)."
                )
            if year < _MIN_BIRTH_YEAR:
                return (
                    f"{year} seems too early to be correct. Please enter a realistic 4-digit "
                    f"birth year between {_MIN_BIRTH_YEAR} and {current_year}."
                )
            if current_year - year > _MAX_REASONABLE_AGE:
                return (
                    "That birth year would imply an age over 110, which is usually a typo. "
                    "Please double-check the year."
                )
        return (
            "I need a 4-digit birth year so I can calculate age-based projections. "
            "For example: \"1982.\""
        )

    if target_field in {
        "income.current_gross_annual",
        "retirement_philosophy.legacy_goal_total_real",
        "accounts.retirement_balance",
        "spending.retirement_monthly_real",
        "social_security.combined_at_67_monthly",
        "social_security.combined_at_70_monthly",
        "monte_carlo.legacy_floor",
    }:
        amount_number = _parse_number(text)
        if amount_number is not None and amount_number < 0:
            return "That amount is negative. Please enter a positive number."
        return (
            "I need a numeric amount for that field. You can enter values like "
            "\"185000\" or \"$185,000.\""
        )

    if target_field in {
        "retirement_philosophy.success_probability_target",
        "monte_carlo.required_success_rate",
        "accounts.savings_rate_percent",
    }:
        percent_number = _parse_number(text)
        if percent_number is not None and "%" in text and percent_number > 100:
            return "That percentage is above 100%. Please enter a value between 0% and 100%."
        if percent_number is not None and percent_number > 100:
            return (
                "That value is too large for a percentage. Please use something like "
                "\"15%\" or \"0.15.\""
            )
        return (
            "I need a percentage for that value. You can reply with something like "
            "\"15%\" or \"0.15.\""
        )

    if target_field == "client.retirement_window":
        range_match = _RANGE_RE.search(text)
        if range_match:
            lo = int(range_match.group(1))
            hi = int(range_match.group(2))
            if lo > hi:
                return (
                    "I read the range backwards. Please share retirement ages from lower to "
                    "higher, like \"62 to 67.\""
                )
            if lo < 40 or hi > 80:
                return "Please use a realistic retirement age range between 40 and 80."
        else:
            single_age = _parse_number(text)
            if single_age is not None and (single_age < 40 or single_age > 80):
                return "Please use a realistic retirement age between 40 and 80."
        return (
            "I need a retirement age or range, like \"65\" or \"65 to 67.\""
        )

    if target_field in {"location.state", "location.city"}:
        if any(ch.isdigit() for ch in text):
            return "That looks like it includes numbers. Please enter a city/state name in words."
        return "I need a place name there (for example, \"Washington\" or \"Seattle\")."

    if target_field == "housing.status":
        return "Please answer with \"rent\" or \"own.\""

    if target_field == "accounts.investment_strategy_id":
        return (
            "Please share a strategy label like \"conservative,\" \"moderate,\" "
            "or \"aggressive.\""
        )

    if target_field == "social_security.claiming_preference":
        claiming_age = _parse_number(text)
        if claiming_age is not None and not (62 <= int(claiming_age) <= 70):
            return "Claiming age should be between 62 and 70."
        return "Please provide a claiming age between 62 and 70 (for example, \"67\")."

    if target_field == "monte_carlo.horizon_age":
        horizon_age = _parse_number(text)
        if horizon_age is not None and not (80 <= int(horizon_age) <= 120):
            return "Projection horizon age is usually between 80 and 120."
        return "Please provide an age for the projection horizon, usually between 80 and 120."

    if target_field == "accounts.has_employer_plan":
        return "Please answer \"yes\" or \"no\" for whether you have an employer retirement plan."

    if target_field in {
        "accounts.employer_match_percent",
        "accounts.employee_contribution_percent",
    }:
        pct_number = _parse_number(text)
        if pct_number is not None and pct_number > 100:
            return "That percentage is above 100%. Please enter a realistic percentage."
        if pct_number is not None and pct_number < 0:
            return "Please enter a positive percentage."
        return "Please enter a percentage, like \"6%\" or \"3\"."

    return None


def _client_friendly_ack(
    applied_paths: list[str],
    schema: CanonicalPlanSchema,
    *,
    previously_populated: set[str] | None = None,
) -> str:
    if not applied_paths:
        return "Thanks for that."

    newly_set = previously_populated is None
    if "client.name" in applied_paths and (newly_set or "client.name" not in previously_populated):
        name_value = _resolve_path_value(schema, "client.name")
        if isinstance(name_value, str) and name_value.strip():
            return f"Hi {name_value}, nice to meet you."
        return "Nice to meet you."

    if "client.birth_year" in applied_paths:
        return "Great, thanks for sharing your birth year."
    if "location.state" in applied_paths or "location.city" in applied_paths:
        return "Perfect, thanks for sharing your location."
    if "income.current_gross_annual" in applied_paths:
        return "Thanks, I have your income."
    if "accounts.retirement_balance" in applied_paths:
        return "Great, I have your retirement balance."
    if "accounts.has_employer_plan" in applied_paths:
        return "Thanks for letting me know about your employer plan."
    if "accounts.employer_match_percent" in applied_paths:
        return "Great, I have your employer match information."
    if "accounts.employee_contribution_percent" in applied_paths:
        return "Perfect, I have your contribution rate."
    if "accounts.savings_rate_percent" in applied_paths:
        return "Great, I have your savings rate."
    if "spending.retirement_monthly_real" in applied_paths:
        return "Thanks, I have your retirement spending target."
    if (
        "social_security.combined_at_67_monthly" in applied_paths
        or "social_security.combined_at_70_monthly" in applied_paths
    ):
        return "Great, I have your Social Security estimate."

    return "Thanks — got it."


def _resolve_path_value(schema: CanonicalPlanSchema, path: str) -> Any:
    current: Any = schema
    for seg in path.split("."):
        if hasattr(current, seg):
            current = getattr(current, seg)
        elif isinstance(current, dict):
            current = current.get(seg)
        else:
            return None
        if current is None:
            return None
    if isinstance(current, ProvenanceField):
        return current.value
    return current


def _is_affirmative(message: str) -> bool:
    normalized = " ".join(message.strip().lower().split())
    return normalized in _AFFIRMATIVE_REPLIES


_LINKED_FIELDS: list[tuple[str, str]] = [
    ("retirement_philosophy.success_probability_target", "monte_carlo.required_success_rate"),
]


def _sync_linked_fields(schema: CanonicalPlanSchema) -> tuple[CanonicalPlanSchema, PatchResult]:
    """Copy values between fields that represent the same concept."""
    patches: list[PatchOp] = []
    for source, target in _LINKED_FIELDS:
        src_val = _resolve_path_value(schema, source)
        tgt_val = _resolve_path_value(schema, target)
        if src_val is not None and (tgt_val is None or tgt_val == 0):
            patches.append(PatchOp(op="set", path=target, value=src_val, confidence=1.0))
    if patches:
        return apply_patches(schema, patches)
    return schema, PatchResult(applied=[], rejected=[], schema_snapshot_id="", warnings=[])


def _populated_paths(schema: CanonicalPlanSchema, paths: list[str]) -> set[str]:
    """Return the subset of *paths* that currently have a meaningful value."""
    populated: set[str] = set()
    for p in paths:
        val = _resolve_path_value(schema, p)
        if val is not None and val != 0 and val != "":
            populated.add(p)
    return populated


class InterviewSession:
    """Manages the state of a single plan interview.

    The session tracks:
    - The canonical schema being built up
    - Conversation history for context
    - The LLM client used for extraction
    """

    def __init__(
        self,
        schema: CanonicalPlanSchema,
        *,
        llm: LLMClient | None = None,
        model: str = "gpt-4o-mini",
        session_id: str | None = None,
    ) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self.schema = schema
        self.llm = llm or StubLLMClient()
        self.model = model
        self.history: list[InterviewMessage] = []
        self.created_at = datetime.now(timezone.utc)

    @property
    def conversation_history(self) -> list[dict[str, str]]:
        """Return conversation history in the format expected by the LLM."""
        return [{"role": m.role, "content": m.content} for m in self.history]

    def start(self) -> InterviewTurnResult:
        """Begin the interview and return the first question."""
        decision = select_next_question(self.schema)
        greeting = welcome_message()
        first_question = decision.next_question or completion_message()
        message = f"{greeting}\n\n{first_question}"

        self.history.append(
            InterviewMessage(role="assistant", content=message)
        )

        return InterviewTurnResult(
            assistant_message=message,
            policy_decision=decision,
            interview_complete=decision.interview_complete,
        )

    async def respond(self, user_message: str) -> InterviewTurnResult:
        """Process a user message and return the next assistant response."""
        self.history.append(
            InterviewMessage(role="user", content=user_message)
        )

        ack_fields = ["client.name"]
        pre_populated = _populated_paths(self.schema, ack_fields)

        try:
            updated_schema, patch_result, decision = await extract_and_apply(
                user_message,
                self.schema,
                self.conversation_history,
                llm=self.llm,
                model=self.model,
            )
        except Exception:
            # Keep interview flow alive even if the model backend times out or fails.
            updated_schema, patch_result = apply_patches(self.schema, [])
            decision = select_next_question(updated_schema)

        if not patch_result.applied:
            fallback_patch = _fallback_patch_for_target(decision.target_field, user_message)
            if fallback_patch is None and decision.target_field and _is_affirmative(user_message):
                existing_value = _resolve_path_value(updated_schema, decision.target_field)
                if existing_value is not None:
                    fallback_patch = PatchOp(
                        op="set",
                        path=decision.target_field,
                        value=existing_value,
                        confidence=1.0,
                    )
            if fallback_patch is not None:
                updated_schema, fallback_result = apply_patches(updated_schema, [fallback_patch])
                patch_result = _merge_patch_results(patch_result, fallback_result)

        updated_schema, _ = _sync_linked_fields(updated_schema)
        decision = select_next_question(updated_schema)
        self.schema = updated_schema

        if decision.interview_complete:
            reply = completion_message()
        elif patch_result.applied:
            applied_paths = [p.path for p in patch_result.applied]
            reply = _client_friendly_ack(applied_paths, updated_schema, previously_populated=pre_populated)
            if decision.next_question:
                reply += f"\n\n{decision.next_question}"
        elif patch_result.rejected:
            feedback = _invalid_input_feedback(decision.target_field, user_message)
            if feedback and decision.next_question:
                reply = f"{feedback}\n\n{decision.next_question}"
            elif decision.next_question:
                reply = (
                    "Thanks — I couldn't use that answer yet. "
                    f"{decision.next_question}"
                )
            else:
                reply = "Thanks — I couldn't use that answer yet. Could you tell me a bit more?"
        else:
            feedback = _invalid_input_feedback(decision.target_field, user_message)
            if feedback and decision.next_question:
                reply = f"{feedback}\n\n{decision.next_question}"
            else:
                reply = decision.next_question or "Could you tell me more?"

        self.history.append(
            InterviewMessage(role="assistant", content=reply)
        )

        return InterviewTurnResult(
            assistant_message=reply,
            patch_result=patch_result,
            policy_decision=decision,
            interview_complete=decision.interview_complete,
        )
