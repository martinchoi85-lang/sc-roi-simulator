"""Unit tests for Korea KEPCO tariff calculator."""

from pathlib import Path
import numpy as np
import pandas as pd
from engine.schema import load_country_config
from engine.tariffs.korea import KoreaTariffCalculator


def test_tariff_300kwh_example():
    """Exact test case requested by user:

    300 kWh in normal month:
    Base 1,600 + Energy 45,460 + Climate 2,700 + Fuel 1,500 = 51,260 KRW
    VAT: 5,126 KRW
    Fund (2.7%): 1,380 KRW (51,260 * 0.027 = 1384.02 -> 1,380 KRW)
    Final total: 57,760 KRW (51,260 + 5,126 + 1,380 = 57,766 -> 57,760 KRW)
    """
    root = Path(__file__).resolve().parent.parent
    cfg = load_country_config(root / "korea")
    calc = KoreaTariffCalculator(cfg.values["tariff"])

    res = calc._calculate_single_month(300.0, month=5)

    assert res["base_fee"] == 1600.0
    assert abs(res["energy_charge"] - 45460.0) < 1.0
    assert res["climate_charge"] == 2700.0
    assert res["fuel_adjust_charge"] == 1500.0
    assert abs(res["variable_fee"] - 49660.0) < 1.0
    assert res["vat"] == 5126.0
    assert res["fund"] == 1380.0
    assert res["total_bill"] == 57760.0


def test_super_user_rate_winter_and_summer():
    """Test super-user rate of 736.2 KRW/kWh above 1,000 kWh in winter and summer."""
    root = Path(__file__).resolve().parent.parent
    cfg = load_country_config(root / "korea")
    calc = KoreaTariffCalculator(cfg.values["tariff"])

    # 1,200 kWh in January (Winter)
    # Tier 1 (200 kWh): 200 * 120.0 = 24,000
    # Tier 2 (200 kWh): 200 * 214.6 = 42,920
    # Tier 3 (600 kWh up to 1000): 600 * 307.3 = 184,380
    # Super user (200 kWh): 200 * 736.2 = 147,240
    # Total energy charge = 24,000 + 42,920 + 184,380 + 147,240 = 398,540
    res_jan = calc._calculate_single_month(1200.0, month=1)
    assert abs(res_jan["energy_charge"] - 398540.0) < 1.0


def test_steady_state_rollover():
    """Test steady-state rollover convergence."""
    root = Path(__file__).resolve().parent.parent
    cfg = load_country_config(root / "korea")
    calc = KoreaTariffCalculator(cfg.values["tariff"])

    dates = pd.date_range("2026-01-01 00:00:00", "2026-12-31 23:45:00", freq="15min")
    n = len(dates)
    # Continuous surplus power
    p_import = np.full(n, 0.4)
    p_export = np.full(n, 0.8)

    bill = calc.calculate_annual_bill(p_import, p_export, dates, "monthly_net")
    # All variable fees eliminated in steady state
    assert bill["annual_billed_kwh"] == 0.0
    assert bill["annual_variable_fee"] == 0.0
    assert bill["steady_state_rollover_kwh"] > 0.0
