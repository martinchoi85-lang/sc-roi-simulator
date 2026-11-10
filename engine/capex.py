"""Capital Expenditure (CAPEX), grid connection fees, and replacement costs model (v9).

Reflecting updated guidelines:
- PV turnkey: low 1,100,000 / central 1,513,667 / high 2,000,000 KRW/kW (includes module, mounting, and inverter).
- Inverter note: "PV 턴키에 포함" (No double counting).
- AWHP turnkey: 14,000,000 KRW (12,000,000 major equipment + 2,000,000 electrical/other).
- ESS: fx=1400, low 396,200 KRW/kWh, central 1,775,200 KRW/kWh, high 1,871,800 KRW/kWh.
- Grid: distribution board 450,000 KRW, wiring 300,000 KRW/kW, KEPCO customer contribution facility fees.
- All models start with 0 pre-installed equipment (incremental logic completely removed).
- Strict validation: sum of components minus subsidies equals net CAPEX within 1 KRW.
"""

from typing import Any, Dict
import numpy as np


def get_pv_turnkey_cost(pv_capacity_kw: float, capex_config: Dict[str, Any], tier: str = "central") -> float:
    """Calculates PV turnkey total cost based on unit cost per kW for each tier."""
    if pv_capacity_kw <= 0.0:
        return 0.0

    pv_cfg = capex_config.get("pv_system", {})
    unit_cfg = pv_cfg.get("unit_cost_per_kw", {})
    tier_val = unit_cfg.get(tier, {})
    if isinstance(tier_val, dict):
        unit_rate = float(tier_val.get("value", 1513667.0))
    else:
        unit_rate = float(tier_val) if tier_val else 1513667.0

    return float(pv_capacity_kw * unit_rate)


def calculate_capex_tier(
    tier: str,
    pv_capacity_kw: float,
    ess_capacity_kwh: float,
    heating_package: str,
    with_subsidy: bool,
    is_off_grid: bool,
    capex_config: Dict[str, Any],
    subsidy_config: Dict[str, Any],
    max_import_kw: float = 0.0,
) -> Dict[str, Any]:
    """Calculates granular CAPEX components for a specific tier ('low', 'central', 'high')."""
    # 1. PV Turnkey (Turnkey includes PV panels, mounting, balance of system, and initial inverter)
    pv_turnkey_total = get_pv_turnkey_cost(pv_capacity_kw, capex_config, tier=tier)
    inverter_capex_note = "PV 턴키에 포함"
    inverter_capex_amount = 0.0

    # 2. ESS Cost
    ess_cfg = capex_config.get("ess_system", {})
    ess_unit_cfg = ess_cfg.get("unit_cost_per_kwh", {}).get(tier, {})
    if isinstance(ess_unit_cfg, dict):
        ess_unit_cost = float(ess_unit_cfg.get("value", 1775200.0))
    else:
        ess_unit_cost = float(ess_unit_cfg) if ess_unit_cfg else 1775200.0
    ess_cost = ess_capacity_kwh * ess_unit_cost

    # 3. AWHP Turnkey (14M KRW flat across tiers)
    is_awhp = "AWHP" in heating_package
    awhp_cfg = capex_config.get("awhp_system", {})
    awhp_turnkey_cfg = awhp_cfg.get("turnkey_installation_cost", {}).get(tier, {})
    if isinstance(awhp_turnkey_cfg, dict):
        awhp_turnkey = float(awhp_turnkey_cfg.get("value", 14000000.0)) if is_awhp else 0.0
    else:
        awhp_turnkey = float(awhp_turnkey_cfg) if is_awhp and awhp_turnkey_cfg else (14000000.0 if is_awhp else 0.0)

    awhp_major_equip = 12000000.0 if is_awhp else 0.0
    awhp_electric_other = 2000000.0 if is_awhp else 0.0

    # 4. Grid Connection & Electrical Work
    grid_cfg = capex_config.get("grid_connection", {})
    base_contract_raw = grid_cfg.get("existing_contract_power_kw", 3.0)
    base_contract = float(base_contract_raw.get("value", 3.0) if isinstance(base_contract_raw, dict) else base_contract_raw)

    if is_off_grid:
        contract_power_kw = 0.0
        dist_board_cost = 0.0
        wiring_cost = 0.0
        grid_facility_cost = 0.0
    else:
        contract_power_kw = max(base_contract, float(pv_capacity_kw), float(max_import_kw))
        contract_power_kw = round(contract_power_kw, 2)
        expansion_kw = max(0.0, contract_power_kw - base_contract)

        dist_board_val = grid_cfg.get("distribution_board_cost", 450000.0)
        dist_board_cost = float(dist_board_val.get("value", 450000.0) if isinstance(dist_board_val, dict) else dist_board_val) if expansion_kw > 0 else 0.0

        wiring_unit_val = grid_cfg.get("wiring_expansion_cost_per_kw", 300000.0)
        wiring_unit = float(wiring_unit_val.get("value", 300000.0) if isinstance(wiring_unit_val, dict) else wiring_unit_val)
        wiring_cost = expansion_kw * wiring_unit

        grid_base_kw = 5.0
        fee_under_5 = 306000.0
        fee_over_5_per_kw = 121000.0
        vat_rate = 0.10

        if contract_power_kw <= grid_base_kw:
            net_charge = fee_under_5
        else:
            net_charge = fee_under_5 + ((contract_power_kw - grid_base_kw) * fee_over_5_per_kw)
        grid_facility_cost = round(net_charge * (1.0 + vat_rate), 0)

    total_grid_electrical_cost = dist_board_cost + wiring_cost + grid_facility_cost

    # Gross CAPEX = PV Turnkey + Inverter(0) + ESS + AWHP + Grid/Electrical
    gross_capex = round(pv_turnkey_total + inverter_capex_amount + ess_cost + awhp_turnkey + total_grid_electrical_cost, 0)

    # 5. Subsidies
    pv_sub = 0.0
    awhp_sub = 0.0
    awhp_sub_sensitivity = 0.0
    ess_sub = 0.0

    if with_subsidy:
        max_pv_thresh = 3.0
        if (not is_off_grid) and (0 < pv_capacity_kw <= max_pv_thresh):
            rate_under_3 = 2650000.0 / 3.0
            pv_sub = round(pv_capacity_kw * rate_under_3, 0)

        # AWHP Subsidy: Base 0 KRW, 70% sensitivity max 9,800,000 KRW
        if is_awhp and awhp_turnkey > 0:
            awhp_sub_sensitivity = min(9800000.0, awhp_turnkey * 0.70)

    total_subsidy = pv_sub + ess_sub + awhp_sub
    net_capex = max(0.0, gross_capex - total_subsidy)
    net_capex_awhp70 = max(0.0, gross_capex - (pv_sub + ess_sub + awhp_sub_sensitivity))

    # Component sum verification
    # Item sum = PV + Inverter(0) + ESS + AWHP + Grid - Subsidy
    component_sum = (
        round(pv_turnkey_total, 0)
        + inverter_capex_amount
        + round(ess_cost, 0)
        + round(awhp_turnkey, 0)
        + round(total_grid_electrical_cost, 0)
        - round(pv_sub, 0)
    )
    is_sum_consistent = abs(component_sum - round(net_capex, 0)) <= 1.0

    # 6. Future Replacement Unit Costs
    rep_cfg = capex_config.get("replacements", {})
    ess_rep_unit_val = rep_cfg.get("ess_replacement_unit_cost_per_kwh", 396200.0)
    ess_rep_unit = float(ess_rep_unit_val.get("value", 396200.0) if isinstance(ess_rep_unit_val, dict) else ess_rep_unit_val)
    ess_replacement_cost = ess_capacity_kwh * ess_rep_unit

    inv_rep_min = 750000.0
    inv_rep_per_kw = 250000.0
    inverter_replacement_cost = max(inv_rep_min, pv_capacity_kw * inv_rep_per_kw) if pv_capacity_kw > 0 else 0.0

    return {
        "tier": tier,
        "contract_power_kw": contract_power_kw,
        "pv_turnkey_cost": round(pv_turnkey_total, 0),
        "inverter_capex_note": inverter_capex_note,
        "inverter_capex_amount": inverter_capex_amount,
        "ess_cost": round(ess_cost, 0),
        "awhp_turnkey_cost": round(awhp_turnkey, 0),
        "awhp_major_equipment_cost": round(awhp_major_equip, 0),
        "awhp_electric_other_cost": round(awhp_electric_other, 0),
        "distribution_board_cost": round(dist_board_cost, 0),
        "wiring_expansion_cost": round(wiring_cost, 0),
        "grid_connection_cost": round(grid_facility_cost, 0),
        "total_grid_electrical_cost": round(total_grid_electrical_cost, 0),
        "gross_capex": round(gross_capex, 0),
        "pv_subsidy": round(pv_sub, 0),
        "awhp_subsidy": round(awhp_sub, 0),
        "awhp_subsidy_sensitivity": round(awhp_sub_sensitivity, 0),
        "ess_subsidy": round(ess_sub, 0),
        "total_subsidy": round(total_subsidy, 0),
        "net_capex": round(net_capex, 0),
        "net_capex_awhp70": round(net_capex_awhp70, 0),
        "component_sum_difference": round(component_sum - net_capex, 2),
        "is_sum_consistent": is_sum_consistent,
        "ess_replacement_cost": round(ess_replacement_cost, 0),
        "inverter_replacement_cost": round(inverter_replacement_cost, 0),
        "pv_replacement_cost": round(pv_turnkey_total, 0),
        "awhp_replacement_cost": round(awhp_turnkey, 0),
    }


def calculate_capex_breakdown(
    pv_capacity_kw: float,
    ess_capacity_kwh: float,
    heating_package: str,
    with_subsidy: bool,
    is_off_grid: bool,
    capex_config: Dict[str, Any],
    subsidy_config: Dict[str, Any],
    max_import_kw: float = 0.0,
) -> Dict[str, Any]:
    """Calculates CAPEX across low, central, and high tiers, returning central as base metrics."""
    res_central = calculate_capex_tier(
        tier="central",
        pv_capacity_kw=pv_capacity_kw,
        ess_capacity_kwh=ess_capacity_kwh,
        heating_package=heating_package,
        with_subsidy=with_subsidy,
        is_off_grid=is_off_grid,
        capex_config=capex_config,
        subsidy_config=subsidy_config,
        max_import_kw=max_import_kw,
    )

    res_low = calculate_capex_tier(
        tier="low",
        pv_capacity_kw=pv_capacity_kw,
        ess_capacity_kwh=ess_capacity_kwh,
        heating_package=heating_package,
        with_subsidy=with_subsidy,
        is_off_grid=is_off_grid,
        capex_config=capex_config,
        subsidy_config=subsidy_config,
        max_import_kw=max_import_kw,
    )

    res_high = calculate_capex_tier(
        tier="high",
        pv_capacity_kw=pv_capacity_kw,
        ess_capacity_kwh=ess_capacity_kwh,
        heating_package=heating_package,
        with_subsidy=with_subsidy,
        is_off_grid=is_off_grid,
        capex_config=capex_config,
        subsidy_config=subsidy_config,
        max_import_kw=max_import_kw,
    )

    combined = dict(res_central)
    combined.update({
        "gross_capex_low": res_low["gross_capex"],
        "gross_capex_central": res_central["gross_capex"],
        "gross_capex_high": res_high["gross_capex"],
        "net_capex_low": res_low["net_capex"],
        "net_capex_central": res_central["net_capex"],
        "net_capex_high": res_high["net_capex"],
        "ess_cost_low": res_low["ess_cost"],
        "ess_cost_central": res_central["ess_cost"],
        "ess_cost_high": res_high["ess_cost"],
        "awhp_cost_low": res_low["awhp_turnkey_cost"],
        "awhp_cost_central": res_central["awhp_turnkey_cost"],
        "awhp_cost_high": res_high["awhp_turnkey_cost"],
        "res_low": res_low,
        "res_central": res_central,
        "res_high": res_high,
    })

    return combined
