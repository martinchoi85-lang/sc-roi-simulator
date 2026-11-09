"""Energy Storage System (ESS) battery charging and discharging simulation."""

from typing import Dict, Any, Tuple
import numpy as np


def simulate_ess_dispatch(
    p_pv_kw: np.ndarray,
    p_load_kw: np.ndarray,
    battery_capacity_kwh: float,
    ess_config: Dict,
    is_off_grid: bool = False,
    dt_hours: float = 0.25,  # 15 minutes
    initial_soc: float = 0.50,
) -> Dict[str, Any]:
    """Simulates 15-minute battery dispatch with self-consumption priority.

    Args:
        p_pv_kw: 15-min PV AC power generation (kW)
        p_load_kw: 15-min total electrical demand (kW)
        battery_capacity_kwh: Nominal battery storage capacity (kWh)
        ess_config: ESS parameters (round_trip_efficiency, soc_min, soc_max, c_rate_max)
        is_off_grid: If True, grid import/export are disabled (curtailment & unmet load tracked)
        dt_hours: Timestep in hours (0.25)
        initial_soc: Initial state of charge fraction (0.0 to 1.0)

    Returns:
        Dictionary of dispatch profiles and summary metrics.
    """
    n = len(p_pv_kw)

    rte = float(ess_config.get("round_trip_efficiency", 0.90))
    eta_chg = np.sqrt(rte)
    eta_dis = np.sqrt(rte)
    soc_min = float(ess_config.get("soc_min", 0.10))
    soc_max = float(ess_config.get("soc_max", 1.00))
    c_rate = float(ess_config.get("c_rate_max", 0.50))

    max_power_kw = battery_capacity_kwh * c_rate

    # Outputs
    soc = np.zeros(n, dtype=float)
    p_chg = np.zeros(n, dtype=float)
    p_dis = np.zeros(n, dtype=float)
    p_import = np.zeros(n, dtype=float)
    p_export = np.zeros(n, dtype=float)
    p_curtail = np.zeros(n, dtype=float)
    p_unmet = np.zeros(n, dtype=float)

    # Initial battery stored energy
    current_stored_kwh = battery_capacity_kwh * initial_soc if battery_capacity_kwh > 0 else 0.0

    for i in range(n):
        net_power = p_pv_kw[i] - p_load_kw[i]

        if battery_capacity_kwh <= 0.0:
            if net_power > 0:
                if is_off_grid:
                    p_curtail[i] = net_power
                else:
                    p_export[i] = net_power
            else:
                deficit = -net_power
                if is_off_grid:
                    p_unmet[i] = deficit
                else:
                    p_import[i] = deficit
            soc[i] = 0.0
            continue

        if net_power > 0:
            # Surplus power: charge battery
            surplus = net_power
            room_kwh = (soc_max * battery_capacity_kwh) - current_stored_kwh
            max_charge_power_energy = max(0.0, room_kwh / (eta_chg * dt_hours))
            charge_power = min(surplus, max_power_kw, max_charge_power_energy)

            p_chg[i] = charge_power
            current_stored_kwh += charge_power * eta_chg * dt_hours

            remaining_surplus = surplus - charge_power
            if remaining_surplus > 1e-5:
                if is_off_grid:
                    p_curtail[i] = remaining_surplus
                else:
                    p_export[i] = remaining_surplus

        else:
            # Deficit power: discharge battery
            deficit = -net_power
            available_kwh = current_stored_kwh - (soc_min * battery_capacity_kwh)
            max_dis_power_energy = max(0.0, (available_kwh * eta_dis) / dt_hours)
            discharge_power = min(deficit, max_power_kw, max_dis_power_energy)

            p_dis[i] = discharge_power
            current_stored_kwh -= (discharge_power / eta_dis) * dt_hours

            remaining_deficit = deficit - discharge_power
            if remaining_deficit > 1e-5:
                if is_off_grid:
                    p_unmet[i] = remaining_deficit
                else:
                    p_import[i] = remaining_deficit

        soc[i] = current_stored_kwh / battery_capacity_kwh if battery_capacity_kwh > 0 else 0.0

    loss_of_load_hours = float(np.sum(p_unmet > 0) * dt_hours)

    return {
        "soc": soc,
        "p_charge_kw": p_chg,
        "p_discharge_kw": p_dis,
        "p_grid_import_kw": p_import,
        "p_grid_export_kw": p_export,
        "p_curtail_kw": p_curtail,
        "p_unmet_kw": p_unmet,
        "loss_of_load_hours": loss_of_load_hours,
        "total_import_kwh": float(np.sum(p_import) * dt_hours),
        "total_export_kwh": float(np.sum(p_export) * dt_hours),
        "total_unmet_kwh": float(np.sum(p_unmet) * dt_hours),
        "total_curtail_kwh": float(np.sum(p_curtail) * dt_hours),
    }


def simulate_ess_dispatch_steady_state(
    p_pv_kw: np.ndarray,
    p_load_kw: np.ndarray,
    battery_capacity_kwh: float,
    ess_config: Dict,
    is_off_grid: bool = False,
    dt_hours: float = 0.25,
    max_iter: int = 5,
    tol: float = 1e-4,
) -> Dict[str, Any]:
    """Runs ESS dispatch iteratively until start SoC matches end-of-year SoC (periodic steady-state)."""
    current_soc_init = 0.50
    final_res = None

    for _ in range(max_iter):
        res = simulate_ess_dispatch(
            p_pv_kw=p_pv_kw,
            p_load_kw=p_load_kw,
            battery_capacity_kwh=battery_capacity_kwh,
            ess_config=ess_config,
            is_off_grid=is_off_grid,
            dt_hours=dt_hours,
            initial_soc=current_soc_init,
        )
        final_res = res
        if battery_capacity_kwh <= 0.0:
            break
        final_soc = res["soc"][-1]
        if abs(final_soc - current_soc_init) < tol:
            break
        current_soc_init = final_soc

    return final_res
