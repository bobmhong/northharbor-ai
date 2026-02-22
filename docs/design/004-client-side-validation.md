# Design: Client-Side Validation and Confidence Refactor

**Status:** Draft
**Author:** @bobmhong
**Created:** 2026-02-22
**Updated:** 2026-02-22

## Summary

Shift the interview validation strategy from LLM-confidence-driven confirmation loops to deterministic client-side validation with a backend fast path, cross-field consistency rules, and a single end-of-interview LLM review. Add a final open-ended "additional considerations" question where the LLM summarizes the client's upcoming life events for use in holistic recommendations. This eliminates the "Thinking..." latency for structured inputs, removes the repeated confirmation prompts, and uses the LLM where it genuinely adds value -- comprehension and synthesis.

## Motivation

The current architecture sends every user response through the LLM extractor, even unambiguous slider and button inputs. This causes:

- **Unnecessary latency:** A 2-5 second LLM round-trip for values the frontend already validated (e.g., a 95% slider selection).
- **Repeated confirmation loops:** The LLM may assign low confidence to clearly valid inputs, triggering confirmation prompts. When the user confirms and the LLM re-extracts with low confidence again, the loop repeats.
- **Poor UX for structured inputs:** Sliders, dropdowns, and yes/no buttons have constrained ranges by definition -- sending them through an LLM adds no value.

The deterministic fallback parsers in `session.py` already handle 100% of structured input parsing correctly. The LLM's role should be limited to genuinely ambiguous free-text inputs and holistic plan review.

## Goals

- Provide instant feedback for invalid inputs via client-side validation (zero round-trip)
- Eliminate the "Thinking..." wait for structured inputs (sliders, buttons, selections)
- Remove the per-field confidence confirmation loop entirely
- Add deterministic cross-field validation rules that catch logical inconsistencies
- Provide a single, comprehensive LLM review when all fields are collected
- Add a final open-ended question for upcoming life events (vacation, wedding, construction, etc.) with LLM-generated summary that feeds into the analysis recommendations

## Non-Goals

- Modifying the Monte Carlo simulation or calculation pipeline
- Replacing the LLM extractor for free-text inputs (it remains for ambiguous text)
- Collecting detailed structured data for additional life events (deferred to a future design)

## Detailed Design

### Overview

The interview flow splits into paths based on input type and interview phase:

```
User Input
    |
    v
Frontend Validation (type, range, format)
    |
    +-- Valid structured input ---> Backend Fast Path (skip LLM, apply directly)
    |
    +-- Free text / ambiguous  ---> Backend LLM Path (existing extractor)
    |
    v
Next Question
    |
    +-- All structured fields collected
         |
         v
    "Anything else to consider?" (open-ended)
         |
         +-- "Nothing else" ---> Skip, move to completion
         |
         +-- Free text ---------> LLM Summarize --> "Did I get that right?"
         |                              ^                    |
         |                              |   (user corrects)  |
         |                              +--------------------+
         |                                   (user confirms)
         v                                        |
    Cross-Field Rules + LLM Review  <-------------+
         |
         v
    Ready for Analysis
```

### Component Changes

**New files:**

- `frontend/src/utils/fieldValidation.ts` -- Per-field validation rules
- `frontend/src/components/interview/WarningsPanel.tsx` -- Right-side panel with running tally of cross-field warnings
- `backend/policy/cross_field_rules.py` -- Deterministic cross-field validation
- `backend/ai/prompts/reviewer.py` -- End-of-interview LLM review prompt
- `backend/ai/prompts/summarizer.py` -- LLM summarization prompt for open-ended input

**Modified files:**

- `frontend/src/components/interview/ChatInput.tsx` -- Validate before send, show inline errors, add `open_text` mode
- `frontend/src/api/client.ts` -- Send `field_path` and `validated` flag
- `frontend/src/pages/InterviewPage.tsx` -- Pass target field context, display warnings
- `backend/interview/router.py` -- Accept new request fields, return warnings
- `backend/interview/session.py` -- Add fast path, remove confirmation loop dependency, add summarization flow
- `backend/policy/engine.py` -- Remove low-confidence confirmation phase from question selection
- `backend/policy/field_registry.py` -- Add `additional_considerations` field group (priority 12)
- `backend/schema/canonical.py` -- Add `additional_considerations` ProvenanceField

### API Changes

**Request -- `POST /api/interview/respond`:**

```python
class RespondRequest(BaseModel):
    session_id: str
    message: str
    field_path: str | None = None   # which field the user is answering
    validated: bool = False          # client-side validation passed
```

**Response -- add `warnings` field:**

```python
class RespondResponse(BaseModel):
    message: str
    target_field: str | None = None
    applied_fields: list[str] = []
    rejected_fields: list[str] = []
    interview_complete: bool = False
    missing_fields: list[str] = []
    warnings: list[str] = []         # cross-field validation warnings
```

### Data Model

**New field on `CanonicalPlanSchema`:**

```python
additional_considerations: ProvenanceField | None = None
```

The `ProvenanceField.value` holds the LLM-generated summary string. The raw user input is preserved in the existing `advisor_interview` dict:

```python
advisor_interview = {
    "considerations_raw": "Big Europe trip next summer, daughter's wedding 2028",
    "considerations_summary": "Two upcoming major expenses: (1) European vacation ..."
}
```

No other schema changes are required. The `advisor_interview` dict is already `dict[str, Any]` with `default_factory=dict`.

### Key Flows

#### Fast path (structured input)

1. User adjusts slider to 95% and clicks Send
2. Frontend validates: 60 <= 95 <= 99, type is number -- valid
3. Frontend sends `{ message: "95%", field_path: "retirement_philosophy.success_probability_target", validated: true }`
4. Backend skips LLM, parses "95%" deterministically, applies patch with confidence 1.0
5. Backend returns next question immediately (no "Thinking..." delay)

#### Slow path (free text)

1. User types "I make about 185k a year before taxes"
2. Frontend detects text mode, no structured validation possible
3. Frontend sends `{ message: "I make about 185k...", field_path: null, validated: false }`
4. Backend invokes LLM extractor as today
5. Fallback parser boosts confidence if LLM is uncertain

#### Cross-field validation

1. User enters SS at 67 = $4,200/mo, then SS at 70 = $3,800/mo
2. Backend applies both patches successfully
3. Cross-field rule fires: "SS at 70 should be >= SS at 67"
4. Warning returned in response: "Social Security benefits typically increase with delayed claiming. Your estimate at 70 ($3,800) is lower than at 67 ($4,200) -- did you mean to reverse these?"
5. Frontend shows warning as a dismissible advisory (not blocking)

#### Additional considerations (open-ended question)

1. All required and prior optional fields collected
2. Policy engine asks: "Before we wrap up, is there anything else you'd like me to consider? For example, an upcoming vacation, a wedding, or new construction."
3. The user has three options:
   - **Provide details:** Type free text describing upcoming events
   - **Skip:** Click "Nothing else" or say "no" -- field marked as answered with value "none", interview moves to completion
   - **Skip to analysis:** Click "Run Analysis" directly -- additional considerations left empty, analysis runs immediately
4. If text provided:
   a. Backend sends user input to LLM with a summarization prompt
   b. LLM returns 2-3 sentence summary focusing on events, timing, and financial impact
   c. Summary stored in `additional_considerations` ProvenanceField; raw input stored in `advisor_interview` dict
   d. Response: "Here's what I understood: [summary]. Did I capture everything?"
5. User confirms ("yes") -> move to completion
6. User adds/corrects -> re-summarize -> ask again
7. Summary is passed to the analysis/recommendation module after Monte Carlo runs

This is the one place in the interview where LLM confirmation is intentional -- the LLM is demonstrating comprehension of unstructured input, not re-validating a slider value.

#### Post-analysis re-entry

After viewing analysis results, the user can return to update additional considerations and rerun the analysis:

1. Dashboard/results page includes an "Update Considerations" action
2. Clicking it navigates back to the interview page with the additional considerations field re-opened for editing
3. The existing summary is shown as context; the user can append, replace, or clear it
4. On submission, the LLM re-summarizes and confirms
5. The user clicks "Rerun Analysis" to regenerate projections with the updated context

#### End-of-interview review

1. All fields collected (including optional + additional considerations), `interview_complete` is true
2. Backend runs deterministic cross-field checks (instant)
3. Backend runs single LLM review of the complete schema (one call)
4. Results returned as structured suggestions with accept/dismiss actions

### Cross-Field Validation Rules

| Rule | Fields | Logic |
|------|--------|-------|
| SS benefits increase with age | `combined_at_67_monthly`, `combined_at_70_monthly` | at_70 >= at_67 |
| Cannot retire in the past | `birth_year`, `retirement_window.min` | retirement_age > current_age |
| Horizon extends past retirement | `horizon_age`, `retirement_window.max` | horizon_age > retirement_max |
| Full match capture | `employee_contribution_pct`, `employer_match_pct` | warn if contribution < 2x match |
| Spending vs income | `retirement_monthly_real`, `current_gross_annual` | warn if monthly > gross/12 |
| Legacy vs balance | `legacy_goal_total_real`, `retirement_balance` | warn if legacy > 10x balance |

**Integration:** Call `run_cross_field_checks(schema)` at the end of `respond()`. Return the full set of active warnings in every response so the frontend can replace (not append) its warnings state.

### Warnings Panel

Cross-field warnings are displayed in a dedicated right-side panel, not inline with chat messages.

**Component:** `frontend/src/components/interview/WarningsPanel.tsx`

- Collapsible panel anchored to the right edge of the interview page
- Badge count shows the number of active warnings (e.g., "2 warnings")
- Each warning shows: rule name, affected fields, user-facing message, and suggested action
- Warnings are dynamically updated after each backend response -- new warnings appear, resolved warnings disappear automatically
- Warnings are non-blocking; the user can proceed through the interview without addressing them
- Clicking a warning's affected field scrolls/highlights the relevant chat message for easy correction

**State management:** The interview store accumulates warnings from each `respond()` call. The backend returns the full set of active warnings on every response (not incremental), so the frontend replaces its list each time.

**Layout:** The interview page shifts from a single-column chat layout to chat + optional right panel when warnings are present. On narrow viewports the panel collapses to a floating badge that expands on tap.

### Error Handling

- **Client validation failure:** Inline error message below the input, send is blocked. No round-trip.
- **Fast path parse failure:** Falls back to the LLM path. The deterministic parser should never fail for structured inputs that passed client validation, but the fallback ensures resilience.
- **LLM timeout/failure:** Existing behavior preserved -- uses empty patches and deterministic fallback.
- **Cross-field warning:** Non-blocking advisory. The user can proceed without addressing it.

## Alternatives Considered

### Alternative 1: Keep LLM extraction for all inputs, fix confidence boosting

Continue sending every response through the LLM but improve the confidence boosting logic (as partially done in the earlier bug fix). Rejected because it adds unnecessary latency for structured inputs and the confidence model is fundamentally fragile -- the LLM may always surprise us with low confidence for clear answers.

### Alternative 2: Remove LLM extraction entirely, use only deterministic parsing

Replace the LLM extractor with a comprehensive rule-based parser. Rejected because free-text inputs genuinely benefit from LLM understanding (e.g., "I make about 185k" -> $185,000, or "I was born in eighty-two" -> 1982). The hybrid approach keeps the LLM where it adds value.

## Security Considerations

- The `validated` flag is a hint, not a trust boundary. The backend deterministic parser re-validates the value regardless. A malicious client cannot bypass server-side checks by sending `validated: true`.
- Input sanitization (strip `$`, commas, `%`) happens on both client and server.

## Performance Considerations

- **Fast path:** Eliminates the 2-5 second LLM round-trip for ~80% of interview interactions (all structured inputs). Response time drops to <100ms for these cases.
- **Additional considerations:** Adds one LLM call for summarization (only when the user provides text, not when skipping). Acceptable because this is inherently a comprehension task.
- **End-of-interview review:** Adds one LLM call at the end. This is acceptable because the user is transitioning to the analysis phase anyway.
- **Cross-field rules:** Deterministic checks add negligible latency (<1ms).
- **Net effect:** Total LLM calls reduced from N (one per field) to 2-3 (free-text extraction + optional summarization + end review).

## Testing Strategy

- **Unit tests:** Validation module (per-field rules), cross-field rules, fast path parsing, skip-detection for "nothing else" replies
- **Integration tests:** Full interview flow with fast path, end-to-end with cross-field warnings, additional considerations summarization + confirmation loop
- **Manual testing:** Walk through the complete interview verifying: no confirmation prompts for structured inputs, open-ended question appears after other optionals, LLM summary is coherent, skip works cleanly

## Migration / Rollout

- The API change (adding optional `field_path` and `validated` fields) is backward-compatible. Existing clients that omit these fields get the current LLM path.
- The confirmation loop removal in `select_next_question()` changes behavior for all clients. This is intentional -- the confirmation loop is a bug, not a feature.
- No data migration needed. Existing sessions continue to work.

## Open Questions

- [ ] Should the end-of-interview LLM review block the user from running analysis, or should it be purely advisory?
- [ ] Are there additional cross-field rules beyond the ones listed that would be valuable?

## Resolved Decisions

- **Cross-field warnings display:** Summary panel, not inline. A right-side warnings panel shows a running tally of active warnings, dynamically updated as fields are answered during the interview.
- **Planned cashflows for known expenses:** Separate future feature. Additional considerations remain purely narrative context in this design; structured cashflow capture is deferred to a dedicated follow-on design.
- **Post-analysis re-entry:** Yes. After viewing analysis results, the user can return to update additional considerations and rerun analysis.

## References

- Related bug fix: confidence boosting loop in `_boost_low_confidence_applied` and `_sync_linked_fields`
- Existing fallback parsers: `backend/interview/session.py` lines 172-270
- Current confidence threshold: `_LOW_CONFIDENCE_THRESHOLD = 0.7` in `session.py`
