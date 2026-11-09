"""Unit tests for cash flow and payback calculation."""

from engine.cashflow import calculate_25y_cashflow


def test_cashflow_payback():
    net_capex = 10_000_000.0  # 10 Million KRW
    baseline_cost = 2_500_000.0
    alt_cost = 500_000.0  # Savings = 2 Million KRW/year
    base_propane = 0.0
    alt_propane = 0.0
    ess_rep = 2_000_000.0  # Incurred at yr 11
    inv_rep = 1_000_000.0  # Incurred at yr 13

    res = calculate_25y_cashflow(
        net_capex=net_capex,
        baseline_annual_cost=baseline_cost,
        alternative_year1_cost=alt_cost,
        baseline_propane_cost=base_propane,
        alternative_propane_cost=alt_propane,
        ess_replacement_cost=ess_rep,
        inverter_replacement_cost=inv_rep,
    )

    # 10M / 2M ~ 5.0 ~ 5.1 years (accounting for 0.5% PV degradation)
    assert 4.8 <= res["payback_years"] <= 5.5
    assert res["payback_period_str"] != ">25"
    assert res["net_savings_25y"] > 0.0

