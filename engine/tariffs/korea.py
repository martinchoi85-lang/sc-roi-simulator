"""Korea KEPCO residential electricity tariff calculator.

Supports:
- Progressive 3-tier tariff for low-voltage residential service.
- Seasonal adjustment (Summer tier limits for July and August).
- Super-user rate: 704.5 KRW/kWh for consumption > 1,000 kWh/month in Winter (Dec-Feb) and Summer (Jul-Aug).
- Electric Power Public Service Fund: 2.7% (with cutoff under 10 KRW).
- Steady-state net metering simulation with rollover convergence (indefinite, limited_months, annual_reset).
- Strict separation of Base Fees vs Variable Charges.
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd
from engine.tariffs.base import BaseTariffCalculator


class KoreaTariffCalculator(BaseTariffCalculator):
    def __init__(self, tariff_config: Dict[str, Any]):
        self.config = tariff_config

        # Base and energy rates
        self.base_std = self.config["base_rates_standard"]
        self.base_sum = self.config["base_rates_summer"]
        self.energy_std = self.config["energy_rates_standard"]
        self.energy_sum = self.config["energy_rates_summer"]

        self.super_user_rate = float(self.config.get("super_user_rate", 704.5))
        self.super_user_limit = float(self.config.get("super_user_threshold_kwh", 1000.0))

        self.climate_rate = float(self.config["climate_rate"])
        self.fuel_adjust_rate = float(self.config["fuel_adjust_rate"])
        self.vat_rate = float(self.config["vat_rate"])
        self.fund_rate = float(self.config["power_fund_rate"])  # 2.7%

        self.rollover_scheme = str(self.config.get("rollover_scheme", "indefinite"))

    def _calculate_single_month(
        self,
        net_kwh: float,
        month: int,
    ) -> Dict[str, float]:
        """Calculates bill components for a single month given net billed kWh."""
        is_summer = month in (7, 8)
        is_winter = month in (12, 1, 2)
        base_rates = self.base_sum if is_summer else self.base_std
        energy_rates = self.energy_sum if is_summer else self.energy_std

        tier1_limit = 300.0 if is_summer else 200.0
        tier2_limit = 450.0 if is_summer else 400.0

        b_t1 = float(base_rates["tier1_up_to_300kwh" if is_summer else "tier1_up_to_200kwh"])
        b_t2 = float(base_rates["tier2_301_to_450kwh" if is_summer else "tier2_201_to_400kwh"])
        b_t3 = float(base_rates["tier3_above_450kwh" if is_summer else "tier3_above_400kwh"])

        e_t1 = float(energy_rates["tier1_up_to_300kwh" if is_summer else "tier1_up_to_200kwh"])
        e_t2 = float(energy_rates["tier2_301_to_450kwh" if is_summer else "tier2_201_to_400kwh"])
        e_t3 = float(energy_rates["tier3_above_450kwh" if is_summer else "tier3_above_400kwh"])

        # Determine Tier and Base Fee
        if net_kwh <= tier1_limit:
            base_fee = b_t1
            energy_charge = net_kwh * e_t1
        elif net_kwh <= tier2_limit:
            base_fee = b_t2
            energy_charge = (tier1_limit * e_t1) + ((net_kwh - tier1_limit) * e_t2)
        else:
            base_fee = b_t3
            # Check super-user threshold (1,000 kWh in winter & summer)
            if (is_summer or is_winter) and (net_kwh > self.super_user_limit):
                tier3_kwh = self.super_user_limit - tier2_limit
                super_kwh = net_kwh - self.super_user_limit
                energy_charge = (
                    (tier1_limit * e_t1)
                    + ((tier2_limit - tier1_limit) * e_t2)
                    + (tier3_kwh * e_t3)
                    + (super_kwh * self.super_user_rate)
                )
            else:
                energy_charge = (
                    (tier1_limit * e_t1)
                    + ((tier2_limit - tier1_limit) * e_t2)
                    + ((net_kwh - tier2_limit) * e_t3)
                )

        climate_charge = net_kwh * self.climate_rate
        fuel_adjust_charge = net_kwh * self.fuel_adjust_rate
        variable_fee = energy_charge + climate_charge + fuel_adjust_charge

        subtotal = base_fee + variable_fee
        vat = round(subtotal * self.vat_rate)
        fund = int(np.floor((subtotal * self.fund_rate) / 10.0) * 10)  # Cut off under 10 KRW
        total_bill = int(np.floor((subtotal + vat + fund) / 10.0) * 10)

        return {
            "billed_kwh": net_kwh,
            "base_fee": base_fee,
            "energy_charge": energy_charge,
            "climate_charge": climate_charge,
            "fuel_adjust_charge": fuel_adjust_charge,
            "variable_fee": variable_fee,
            "vat": float(vat),
            "fund": float(fund),
            "total_bill": float(total_bill),
        }

    def _simulate_12_months_pass(
        self,
        monthly_import_kwh: np.ndarray,
        monthly_export_kwh: np.ndarray,
        initial_rollover_kwh: float,
        net_metering_scheme: str,
    ) -> Tuple[List[Dict[str, float]], float]:
        """Runs a 1-year sequential monthly billing pass starting with an initial rollover."""
        monthly_results = []
        carried = initial_rollover_kwh

        for m in range(1, 13):
            m_imp = monthly_import_kwh[m - 1]
            m_exp = monthly_export_kwh[m - 1]

            if net_metering_scheme == "monthly_net":
                total_credits = m_exp + carried
                if m_imp >= total_credits:
                    billed_kwh = m_imp - total_credits
                    carried = 0.0
                else:
                    billed_kwh = 0.0
                    carried = total_credits - m_imp

                # End of year reset check
                if m == 12 and self.rollover_scheme == "annual_reset":
                    carried = 0.0

            elif net_metering_scheme == "tou_slot_net":
                billed_kwh = m_imp  # slot-netted upstream
                carried = 0.0
            else:
                raise ValueError(f"Unsupported net metering scheme: {net_metering_scheme}")

            m_calc = self._calculate_single_month(billed_kwh, m)
            m_calc["month"] = m
            m_calc["import_kwh"] = m_imp
            m_calc["export_kwh"] = m_exp
            m_calc["carried_rollover_kwh"] = carried
            monthly_results.append(m_calc)

        return monthly_results, carried

    def calculate_annual_bill(
        self,
        p_grid_import_kw: np.ndarray,
        p_grid_export_kw: np.ndarray,
        dates: pd.DatetimeIndex,
        net_metering_scheme: str = "monthly_net",
    ) -> Dict[str, Any]:
        """Calculates steady-state 12-month billing details with rollover convergence."""
        months = dates.month.values
        dt_h = 0.25

        m_idx = months - 1
        if net_metering_scheme == "tou_slot_net":
            slot_net_imp = np.maximum(0.0, p_grid_import_kw - p_grid_export_kw)
            slot_net_exp = np.maximum(0.0, p_grid_export_kw - p_grid_import_kw)
            monthly_import_kwh = np.bincount(m_idx, weights=slot_net_imp, minlength=12) * dt_h
            monthly_export_kwh = np.bincount(m_idx, weights=slot_net_exp, minlength=12) * dt_h
        else:
            monthly_import_kwh = np.bincount(m_idx, weights=p_grid_import_kw, minlength=12) * dt_h
            monthly_export_kwh = np.bincount(m_idx, weights=p_grid_export_kw, minlength=12) * dt_h

        # Steady-state fixed-point iteration for rollover
        carried_start = 0.0
        max_iters = 10
        converged_results = None
        final_carried = 0.0

        if net_metering_scheme == "monthly_net" and self.rollover_scheme == "indefinite":
            for _ in range(max_iters):
                m_results, carried_end = self._simulate_12_months_pass(
                    monthly_import_kwh, monthly_export_kwh, carried_start, net_metering_scheme
                )
                if abs(carried_end - carried_start) < 0.01:
                    converged_results = m_results
                    final_carried = carried_end
                    break
                carried_start = carried_end
            if converged_results is None:
                converged_results, final_carried = self._simulate_12_months_pass(
                    monthly_import_kwh, monthly_export_kwh, carried_start, net_metering_scheme
                )
        else:
            converged_results, final_carried = self._simulate_12_months_pass(
                monthly_import_kwh, monthly_export_kwh, 0.0, net_metering_scheme
            )

        annual_base_fee = sum(r["base_fee"] for r in converged_results)
        annual_variable_fee = sum(r["variable_fee"] for r in converged_results)
        annual_vat_and_fund = sum(r["vat"] + r["fund"] for r in converged_results)
        annual_total_bill = sum(r["total_bill"] for r in converged_results)
        annual_billed_kwh = sum(r["billed_kwh"] for r in converged_results)

        return {
            "annual_total_bill": float(annual_total_bill),
            "annual_base_fee": float(annual_base_fee),
            "annual_variable_fee": float(annual_variable_fee),
            "annual_vat_and_fund": float(annual_vat_and_fund),
            "annual_billed_kwh": float(annual_billed_kwh),
            "steady_state_rollover_kwh": float(final_carried),
            "monthly_details": converged_results,
        }
