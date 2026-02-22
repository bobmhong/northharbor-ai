export interface ValidationResult {
  valid: boolean;
  error?: string;
}

export function sanitize(value: string): string {
  return value.trim().replace(/[$,%]/g, "").replace(/,/g, "");
}

const DOLLAR_FIELDS = new Set([
  "income.current_gross_annual",
  "retirement_philosophy.legacy_goal_total_real",
  "accounts.retirement_balance",
  "spending.retirement_monthly_real",
  "social_security.combined_at_67_monthly",
  "social_security.combined_at_70_monthly",
  "monte_carlo.legacy_floor",
]);

const RENT_SYNONYMS = new Set(["rent", "renting", "renter"]);
const OWN_SYNONYMS = new Set(["own", "owning", "owner"]);

function ok(): ValidationResult {
  return { valid: true };
}

function fail(error: string): ValidationResult {
  return { valid: false, error };
}

function validateName(value: string): ValidationResult {
  const words = value.split(/\s+/).filter(Boolean);
  if (words.length < 2 || words.length > 4) {
    return fail("Please enter your full name (first and last).");
  }
  const namePattern = /^[A-Z][a-zA-Z'-]*$/;
  if (!words.every((w) => namePattern.test(w))) {
    return fail("Please enter your full name (first and last).");
  }
  return ok();
}

function validateBirthYear(value: string): ValidationResult {
  if (!/^\d{4}$/.test(value)) {
    return fail("Please enter a 4-digit year.");
  }
  const year = parseInt(value, 10);
  const currentYear = new Date().getFullYear();
  if (year < 1900 || year > currentYear) {
    return fail(`Year must be between 1900 and ${currentYear}.`);
  }
  return ok();
}

function validateLocationName(value: string): ValidationResult {
  if (!value || !/^[A-Za-z\s]+$/.test(value)) {
    return fail("Please enter a valid location name.");
  }
  return ok();
}

function validateDollarAmount(value: string): ValidationResult {
  const num = Number(value);
  if (value === "" || isNaN(num) || num < 0) {
    return fail("Please enter a valid dollar amount.");
  }
  return ok();
}

function validateSuccessRate(value: string): ValidationResult {
  let num = Number(value);
  if (value === "" || isNaN(num)) {
    return fail("Success rate must be between 60% and 99%.");
  }
  if (num > 1) num /= 100;
  if (num < 0.6 || num > 0.99) {
    return fail("Success rate must be between 60% and 99%.");
  }
  return ok();
}

function validatePercentRange(
  value: string,
  min: number,
  max: number,
  error: string,
): ValidationResult {
  const num = Number(value);
  if (value === "" || isNaN(num) || num < min || num > max) {
    return fail(error);
  }
  return ok();
}

function validateRetirementWindow(raw: string): ValidationResult {
  const err = fail("Retirement age must be between 40 and 80.");
  const rangeMatch = raw.match(/^(\d+)\s*(?:to|-)\s*(\d+)$/i);
  if (rangeMatch) {
    const lo = parseInt(rangeMatch[1], 10);
    const hi = parseInt(rangeMatch[2], 10);
    if (lo < 40 || hi > 80 || lo > hi) return err;
    return ok();
  }
  const single = parseInt(raw, 10);
  if (isNaN(single) || String(single) !== raw.trim()) return err;
  if (single < 40 || single > 80) return err;
  return ok();
}

function validateBoolean(value: string): ValidationResult {
  const lower = value.toLowerCase();
  if (["yes", "no", "true", "false"].includes(lower)) return ok();
  return fail("Please answer yes or no.");
}

function validateIntRange(
  value: string,
  min: number,
  max: number,
  error: string,
): ValidationResult {
  const num = parseInt(value, 10);
  if (isNaN(num) || String(num) !== value.trim() || num < min || num > max) {
    return fail(error);
  }
  return ok();
}

function validateHousingStatus(value: string): ValidationResult {
  const lower = value.toLowerCase();
  if (RENT_SYNONYMS.has(lower) || OWN_SYNONYMS.has(lower)) return ok();
  return fail("Please answer rent or own.");
}

function validateNonEmpty(value: string, error: string): ValidationResult {
  if (!value) return fail(error);
  return ok();
}

export function validateField(
  fieldPath: string,
  rawValue: string,
): ValidationResult {
  const value = sanitize(rawValue);

  if (fieldPath === "client.name") return validateName(value);
  if (fieldPath === "client.birth_year") return validateBirthYear(value);
  if (fieldPath === "location.state" || fieldPath === "location.city")
    return validateLocationName(value);
  if (DOLLAR_FIELDS.has(fieldPath)) return validateDollarAmount(value);
  if (
    fieldPath === "retirement_philosophy.success_probability_target" ||
    fieldPath === "monte_carlo.required_success_rate"
  )
    return validateSuccessRate(value);
  if (fieldPath === "accounts.savings_rate_percent")
    return validatePercentRange(
      value,
      0,
      100,
      "Savings rate must be between 0% and 100%.",
    );
  if (fieldPath === "accounts.employer_match_percent")
    return validatePercentRange(
      value,
      0,
      100,
      "Match percentage must be between 0% and 100%.",
    );
  if (fieldPath === "accounts.employee_contribution_percent")
    return validatePercentRange(
      value,
      0,
      100,
      "Contribution must be between 0% and 100%.",
    );
  if (fieldPath === "client.retirement_window")
    return validateRetirementWindow(rawValue.trim());
  if (fieldPath === "accounts.has_employer_plan") return validateBoolean(value);
  if (fieldPath === "social_security.claiming_preference")
    return validateIntRange(
      value,
      62,
      70,
      "Claiming age must be between 62 and 70.",
    );
  if (fieldPath === "monte_carlo.horizon_age")
    return validateIntRange(
      value,
      80,
      120,
      "Horizon age must be between 80 and 120.",
    );
  if (fieldPath === "housing.status") return validateHousingStatus(value);
  if (fieldPath === "accounts.investment_strategy_id")
    return validateNonEmpty(
      value,
      "Please describe your investment strategy.",
    );

  return ok();
}
