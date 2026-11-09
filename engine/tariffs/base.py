"""Abstract Base Class for Country-Specific Electricity Tariff Calculations."""

from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np
import pandas as pd


class BaseTariffCalculator(ABC):
    """Abstract interface for country electricity tariff calculation."""

    @abstractmethod
    def calculate_annual_bill(
        self,
        p_grid_import_kw: np.ndarray,
        p_grid_export_kw: np.ndarray,
        dates: pd.DatetimeIndex,
        net_metering_scheme: str = "monthly_net",
    ) -> Dict[str, Any]:
        """Calculates the 12-month billing details, annual base fee, and variable fee.

        Args:
            p_grid_import_kw: 15-minute grid import profile (kW)
            p_grid_export_kw: 15-minute grid export profile (kW)
            dates: 35,040 DatetimeIndex
            net_metering_scheme: 'monthly_net' or other country-specific schemes

        Returns:
            Dictionary containing:
            - 'annual_total_bill': Total electricity bill in local currency
            - 'annual_base_fee': Sum of monthly base fees
            - 'annual_variable_fee': Sum of variable charges (energy, climate, fuel, etc.)
            - 'annual_vat_and_fund': Taxes and funds
            - 'monthly_details': List of 12 monthly bill breakdown dicts
        """
        pass

