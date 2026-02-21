"""Table generation stage.

Converts pipeline outputs into structured table specs for the frontend.
"""

from __future__ import annotations

from typing import Any


def generate_tables(
    inputs: dict[str, Any],
    derived: dict[str, Any],
    mc_results: dict[str, Any],
    backtest_results: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate structured table specifications from pipeline results."""
    tables: list[dict[str, Any]] = []

    base_results = mc_results.get("base_results", [])
    if base_results:
        rows = []
        for r in base_results:
            p = r.get("terminal_balance_percentiles_real", {})
            balance_info = derived.get("projected_balances_base_case_real", {})
            age = r["retirement_age"]
            rows.append({
                "retirement_age": age,
                "projected_balance": balance_info.get(f"age_{age}", 0),
                "success_probability": r["success_probability"],
                "terminal_p05": p.get("p05", 0),
                "terminal_p25": p.get("p25", 0),
                "terminal_p50": p.get("p50", 0),
                "terminal_p75": p.get("p75", 0),
                "terminal_p95": p.get("p95", 0),
            })
        tables.append({
            "id": "retirement_age_summary",
            "title": "Retirement Age Summary",
            "section": "dashboard",
            "columns": [
                {"key": "retirement_age", "label": "Retirement Age", "format": "integer"},
                {"key": "projected_balance", "label": "Projected Balance", "format": "currency"},
                {"key": "success_probability", "label": "Success Probability", "format": "percent"},
                {"key": "terminal_p50", "label": "Median Terminal Balance", "format": "currency"},
            ],
            "rows": rows,
        })

    wa = derived.get("withdrawal_analysis", {})
    wa_rows = []
    for key, val in wa.items():
        if key.startswith("age_") and isinstance(val, dict):
            age = int(key.split("_")[1])
            wa_rows.append({
                "retirement_age": age,
                "withdrawal_4pct": val.get("annual_withdrawal_4_percent", 0),
                "ss_annual": val.get("social_security_annual", 0),
                "annual_spending": val.get("annual_spending", 0),
                "portfolio_needed": val.get("portfolio_needed_after_ss", 0),
                "effective_rate": val.get("effective_withdrawal_rate", 0),
            })
    if wa_rows:
        tables.append({
            "id": "withdrawal_analysis",
            "title": "Withdrawal Analysis",
            "section": "appendix",
            "columns": [
                {"key": "retirement_age", "label": "Age", "format": "integer"},
                {"key": "withdrawal_4pct", "label": "4% Withdrawal", "format": "currency"},
                {"key": "ss_annual", "label": "Social Security", "format": "currency"},
                {"key": "annual_spending", "label": "Annual Spending", "format": "currency"},
                {"key": "portfolio_needed", "label": "Portfolio Needed", "format": "currency"},
                {"key": "effective_rate", "label": "Withdrawal Rate", "format": "percent"},
            ],
            "rows": wa_rows,
        })

    comparisons = backtest_results.get("period_comparisons", [])
    if comparisons:
        bt_rows = [{
            "period": c["label"],
            "success": c["success"],
            "terminal_balance": c["terminal_balance_real"],
            "delta_vs_baseline": c["delta_terminal_vs_baseline_p50"],
        } for c in comparisons]
        tables.append({
            "id": "backtest_comparison",
            "title": "Historical Backtest Comparison",
            "section": "appendix",
            "columns": [
                {"key": "period", "label": "Historical Period", "format": "text"},
                {"key": "success", "label": "Survived?", "format": "boolean"},
                {"key": "terminal_balance", "label": "Terminal Balance", "format": "currency"},
                {"key": "delta_vs_baseline", "label": "Delta vs Baseline", "format": "currency"},
            ],
            "rows": bt_rows,
        })

    return tables
