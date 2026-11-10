"""Unit tests for 100-year cash flow and payback calculation (v9)."""

from engine.cashflow import calculate_100y_cashflow


def test_cashflow_payback_normal():
    """Test normal payback period calculation with linear interpolation."""
    res = calculate_100y_cashflow(
        net_capex=10_000_000.0,
        baseline_annual_cost=2_500_000.0,
        alternative_year1_cost=500_000.0,
        baseline_propane_cost=0.0,
        alternative_propane_cost=0.0,
        pv_capacity_kw=3.0,
        ess_capacity_kwh=9.6,
        is_awhp=False,
        pv_turnkey_cost=4_541_000.0,
        inverter_replacement_cost=750_000.0,
        ess_replacement_cost=3_803_520.0,
        awhp_replacement_cost=0.0,
    )
    assert res["payback_years"] is not None
    assert res["reason_code"] in ["PAYBACK_ACHIEVED", "PAYBACK_RECOVERED"]
    assert res["payback_period_str"] == f"{res['payback_years']:.1f}"
    assert res["net_savings_25y"] > 0
    assert res["net_savings_100y"] > 0


def test_cashflow_boundary_no_savings():
    """Test boundary case: Annual savings <= 0."""
    res = calculate_100y_cashflow(
        net_capex=10_000_000.0,
        baseline_annual_cost=1_000_000.0,
        alternative_year1_cost=1_200_000.0,
        baseline_propane_cost=0.0,
        alternative_propane_cost=0.0,
    )
    assert res["payback_years"] is None
    assert res["payback_period_str"] == "불가능(연간 이득 없음)"
    assert res["reason_code"] == "NO_ANNUAL_SAVINGS"


def test_cashflow_boundary_not_recovered_100y():
    """Test boundary case: Cannot recover within 100 years."""
    res = calculate_100y_cashflow(
        net_capex=50_000_000.0,
        baseline_annual_cost=1_000_000.0,
        alternative_year1_cost=900_000.0,
        baseline_propane_cost=0.0,
        alternative_propane_cost=0.0,
    )
    assert res["payback_years"] is None
    assert res["payback_period_str"] == "불가능"
    assert res["reason_code"] == "NOT_RECOVERED_100Y"


def test_cashflow_boundary_relapse_after_replacement():
    """Test boundary case: Relapse to negative due to equipment replacement."""
    # Net CAPEX 5M, savings 1M/yr -> crosses 0 around yr 5.
    # But huge replacement at yr 10 dips cum_cf back below 0.
    res = calculate_100y_cashflow(
        net_capex=5_000_000.0,
        baseline_annual_cost=1_500_000.0,
        alternative_year1_cost=500_000.0,
        baseline_propane_cost=0.0,
        alternative_propane_cost=0.0,
        pv_capacity_kw=0.0,
        ess_capacity_kwh=10.0,
        ess_replacement_cost=8_000_000.0,  # huge replacement
    )
    # The payback must be after the last dip
    if res["payback_years"] is not None:
        assert res["payback_years"] > 11.0
