export interface FieldConfig {
  path: string;
  label: string;
  type: "text" | "currency" | "percentage" | "number" | "boolean" | "age_range";
  min?: number;
  max?: number;
}

export interface FieldGroup {
  group: string;
  fields: FieldConfig[];
}

export const REVIEW_FIELDS: FieldGroup[] = [
  {
    group: "About You",
    fields: [
      { path: "client.name", label: "Name", type: "text" },
      { path: "client.birth_year", label: "Birth Year", type: "number", min: 1930, max: 2010 },
      { path: "client.retirement_window", label: "Target Retirement Age", type: "age_range" },
    ],
  },
  {
    group: "Location",
    fields: [
      { path: "location.state", label: "State", type: "text" },
      { path: "location.city", label: "City", type: "text" },
    ],
  },
  {
    group: "Income & Savings",
    fields: [
      { path: "income.current_gross_annual", label: "Annual Income", type: "currency" },
      { path: "accounts.retirement_balance", label: "Retirement Balance", type: "currency" },
      { path: "accounts.has_employer_plan", label: "Employer Plan", type: "boolean" },
      { path: "accounts.employer_match_percent", label: "Employer Match", type: "percentage", min: 0, max: 100 },
      { path: "accounts.employee_contribution_percent", label: "Your Contribution", type: "percentage", min: 0, max: 100 },
      { path: "accounts.savings_rate_percent", label: "Savings Rate", type: "percentage", min: 0, max: 100 },
    ],
  },
  {
    group: "Retirement Spending",
    fields: [
      { path: "spending.retirement_monthly_real", label: "Monthly Spending", type: "currency" },
    ],
  },
  {
    group: "Social Security",
    fields: [
      { path: "social_security.combined_at_67_monthly", label: "Benefit at 67", type: "currency" },
      { path: "social_security.combined_at_70_monthly", label: "Benefit at 70", type: "currency" },
    ],
  },
  {
    group: "Goals & Preferences",
    fields: [
      { path: "retirement_philosophy.success_probability_target", label: "Target Success Rate", type: "percentage", min: 50, max: 99 },
      { path: "retirement_philosophy.legacy_goal_total_real", label: "Legacy Goal", type: "currency" },
      { path: "monte_carlo.horizon_age", label: "Plan Through Age", type: "number", min: 80, max: 110 },
      { path: "monte_carlo.legacy_floor", label: "Minimum Legacy", type: "currency" },
    ],
  },
];
