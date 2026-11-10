"""Comprehensive v9 verification test suite satisfying requirement #12."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from engine.schema import load_country_config
from engine.tariffs.korea import KoreaTariffCalculator
from engine.occupancy import generate_occupancy_calendar
from engine.occupancy_tus import OccupancyTUSModel
from engine.weather import load_weather_data
from engine.cashflow import calculate_100y_cashflow
from engine.capex import calculate_capex_breakdown
from engine.scenarios import run_all_scenarios


@pytest.fixture(scope="session")
def project_data():
    root = Path(__file__).resolve().parent.parent
    cfg = load_country_config(root / "korea")
    weather_df = load_weather_data(root / "korea" / "source" / "tmy_chuncheon_471010_15min.csv")
    return root, cfg, weather_df


def test_req1_kepco_300kwh_bill(project_data):
    """Test 1: 300kWh normal month electricity bill == 57,760 KRW."""
    _, cfg, _ = project_data
    calc = KoreaTariffCalculator(cfg.values["tariff"])
    res = calc._calculate_single_month(300.0, month=5)
    assert res["total_bill"] == 57760.0


def test_req2_occupancy_days_exact_round():
    """Test 2: Occupied days count == round(365 * occupancy_rate)."""
    rates = [1.00, 0.70, 0.50, 0.30, 0.15]
    for rate in rates:
        is_occ_day, _, _ = generate_occupancy_calendar(rate)
        expected = int(round(365 * rate))
        assert is_occ_day.sum() == expected


def test_req3_appliance_calibration_error(project_data):
    """Test 3: Appliance annual kWh calibration error <= 0.5%."""
    root, cfg, weather_df = project_data
    model = OccupancyTUSModel(
        kosis_dir=root / "korea" / "source" / "kosis",
        load_config=cfg.values["load"],
        house_config=cfg.values["houses"]["MONO Core 54"],
        weather_df=weather_df,
        occupants=2,
        seed=42,
    )
    res = model.simulate_year(occupancy_rate=1.0)
    for app, err in res["appliance_calibration_errors"].items():
        assert err <= 0.5, f"Appliance {app} calibration error {err}% exceeds 0.5%"


def test_req4_payback_boundary_cases():
    """Test 4: Cash flow boundary cases (gain <= 0, > 100 years, relapse after replacement)."""
    # 4a: Gain <= 0 -> "불가능(연간 이득 없음)", reason "NO_ANNUAL_SAVINGS"
    r1 = calculate_100y_cashflow(10_000_000.0, 1_000_000.0, 1_200_000.0, 0.0, 0.0)
    assert r1["payback_years"] is None
    assert r1["payback_period_str"] == "불가능(연간 이득 없음)"
    assert r1["reason_code"] == "NO_ANNUAL_SAVINGS"

    # 4b: > 100 years -> "불가능", reason "NOT_RECOVERED_100Y"
    r2 = calculate_100y_cashflow(50_000_000.0, 1_000_000.0, 900_000.0, 0.0, 0.0)
    assert r2["payback_years"] is None
    assert r2["payback_period_str"] == "불가능"
    assert r2["reason_code"] == "NOT_RECOVERED_100Y"

    # 4c: Relapse after replacement
    r3 = calculate_100y_cashflow(
        5_000_000.0, 1_500_000.0, 500_000.0, 0.0, 0.0,
        pv_capacity_kw=0.0, ess_capacity_kwh=10.0, ess_replacement_cost=8_000_000.0
    )
    if r3["payback_years"] is not None:
        assert r3["payback_years"] > 11.0


def test_req5_capex_components_sum(project_data):
    """Test 5: CAPEX component sum == net CAPEX within 1 KRW."""
    _, cfg, _ = project_data
    capex_cfg = cfg.values["capex"]
    subsidy_cfg = cfg.values["subsidy"]

    for pv in [0.0, 3.0, 6.0]:
        for ess in [0.0, 9.6, 19.2]:
            for heat in ["가스보일러", "AWHP"]:
                for sub in [False, True]:
                    for offgrid in [False, True]:
                        res = calculate_capex_breakdown(
                            pv_capacity_kw=pv,
                            ess_capacity_kwh=ess,
                            heating_package=heat,
                            with_subsidy=sub,
                            is_off_grid=offgrid,
                            capex_config=capex_cfg,
                            subsidy_config=subsidy_cfg,
                        )
                        assert res["is_sum_consistent"], f"CAPEX sum mismatch: diff={res['component_sum_difference']}"
                        assert abs(res["component_sum_difference"]) <= 1.0


def test_req6_scenarios_count_420(project_data):
    """Test 6: Exactly 420 scenarios generated."""
    root, cfg, weather_df = project_data
    df_results, df_energy_comp, df_ze_sizing, _ = run_all_scenarios(
        config_values=cfg.values,
        weather_df=weather_df,
        kosis_dir=root / "korea" / "source" / "kosis",
    )
    assert len(df_results) == 420
    assert len(df_energy_comp) == 420
    assert len(df_ze_sizing) == 70

