"""Chart specification generation stage.

Produces declarative ECharts option objects from pipeline results for
frontend rendering.
"""

from __future__ import annotations

from typing import Any


def generate_chart_specs(
    inputs: dict[str, Any],
    derived: dict[str, Any],
    mc_results: dict[str, Any],
    backtest_results: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate ECharts chart specifications from pipeline results."""
    charts: list[dict[str, Any]] = []

    base_results = mc_results.get("base_results", [])
    if base_results:
        ages = [r["retirement_age"] for r in base_results]
        probs = [round(r["success_probability"] * 100, 1) for r in base_results]
        target = mc_results.get("assessment", {}).get(
            "minimum_success_probability_target", 0.95
        )

        charts.append({
            "id": "success_by_age",
            "title": "Success Probability by Retirement Age",
            "chart_type": "bar",
            "description": "Monte Carlo success probability at each retirement age",
            "section": "dashboard",
            "data_source": "retirement_age_summary",
            "echarts_option": {
                "xAxis": {"type": "category", "data": ages, "name": "Retirement Age"},
                "yAxis": {"type": "value", "name": "Success %", "max": 100},
                "series": [{
                    "type": "bar",
                    "data": probs,
                    "itemStyle": {"color": "#4f8df7"},
                }],
                "markLine": {
                    "data": [{"yAxis": round(target * 100, 1), "name": "Target"}]
                },
                "tooltip": {"trigger": "axis"},
            },
        })

    if base_results:
        ages = [r["retirement_age"] for r in base_results]
        p05 = [r.get("terminal_balance_percentiles_real", {}).get("p05", 0) for r in base_results]
        p25 = [r.get("terminal_balance_percentiles_real", {}).get("p25", 0) for r in base_results]
        p50 = [r.get("terminal_balance_percentiles_real", {}).get("p50", 0) for r in base_results]
        p75 = [r.get("terminal_balance_percentiles_real", {}).get("p75", 0) for r in base_results]
        p95 = [r.get("terminal_balance_percentiles_real", {}).get("p95", 0) for r in base_results]

        charts.append({
            "id": "terminal_balance_range",
            "title": "Terminal Balance Distribution by Retirement Age",
            "chart_type": "line",
            "description": "Percentile bands of terminal balance at each retirement age",
            "section": "dashboard",
            "data_source": "retirement_age_summary",
            "echarts_option": {
                "xAxis": {"type": "category", "data": ages, "name": "Retirement Age"},
                "yAxis": {"type": "value", "name": "Terminal Balance ($)"},
                "series": [
                    {"name": "p95", "type": "line", "data": p95, "lineStyle": {"type": "dashed"}},
                    {"name": "p75", "type": "line", "data": p75},
                    {"name": "p50 (Median)", "type": "line", "data": p50, "lineStyle": {"width": 3}},
                    {"name": "p25", "type": "line", "data": p25},
                    {"name": "p05", "type": "line", "data": p05, "lineStyle": {"type": "dashed"}},
                ],
                "tooltip": {"trigger": "axis"},
                "legend": {"data": ["p95", "p75", "p50 (Median)", "p25", "p05"]},
            },
        })

    balances = derived.get("projected_balances_base_case_real", {})
    if balances:
        sorted_ages = sorted(int(k.split("_")[1]) for k in balances if k.startswith("age_"))
        vals = [balances[f"age_{a}"] for a in sorted_ages]
        charts.append({
            "id": "projected_balance_growth",
            "title": "Projected Balance Growth",
            "chart_type": "area",
            "description": "Projected retirement balance at each age",
            "section": "dashboard",
            "data_source": "withdrawal_analysis",
            "echarts_option": {
                "xAxis": {"type": "category", "data": sorted_ages, "name": "Age"},
                "yAxis": {"type": "value", "name": "Balance ($)"},
                "series": [{
                    "type": "line",
                    "data": vals,
                    "areaStyle": {"opacity": 0.3},
                    "itemStyle": {"color": "#22c55e"},
                }],
                "tooltip": {"trigger": "axis"},
            },
        })

    comparisons = backtest_results.get("period_comparisons", [])
    if comparisons:
        labels = [c["label"] for c in comparisons]
        terminals = [c["terminal_balance_real"] for c in comparisons]
        colors = ["#22c55e" if c["success"] else "#ef4444" for c in comparisons]

        charts.append({
            "id": "backtest_results",
            "title": "Historical Backtest Results",
            "chart_type": "bar",
            "description": "Terminal balance under historical market periods",
            "section": "appendix",
            "data_source": "backtest_comparison",
            "echarts_option": {
                "xAxis": {"type": "category", "data": labels, "axisLabel": {"rotate": 30}},
                "yAxis": {"type": "value", "name": "Terminal Balance ($)"},
                "series": [{
                    "type": "bar",
                    "data": [
                        {"value": t, "itemStyle": {"color": c}}
                        for t, c in zip(terminals, colors)
                    ],
                }],
                "tooltip": {"trigger": "axis"},
            },
        })

    return charts
