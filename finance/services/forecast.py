from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Dict, Any

import numpy as np


@dataclass
class ForecastResult:
    status: str  # ok | insufficient_data
    predicted_profit: Optional[Decimal]
    lower: Optional[Decimal]
    upper: Optional[Decimal]
    algorithm: Optional[str]
    used_months: int


class ForecastService:
    """Profit forecasting based on monthly summaries."""

    @staticmethod
    def forecast_next_month(history: List[object]) -> ForecastResult:
        """
        Args:
            history: list of MonthlySummary-like objects with .profit and .month_key.
                    Must be ordered ascending by month.
        """
        if len(history) < 3:
            return ForecastResult(
                status='insufficient_data',
                predicted_profit=None,
                lower=None,
                upper=None,
                algorithm=None,
                used_months=len(history),
            )

        profits = np.array([float(s.profit) for s in history], dtype=float)
        x = np.arange(len(profits), dtype=float)

        coef = np.polyfit(x, profits, 1)
        p = np.poly1d(coef)
        y_hat = p(x)
        residuals = profits - y_hat

        forecast_value = float(p(len(profits)))

        if len(residuals) >= 2:
            std = float(np.std(residuals, ddof=1))
        else:
            std = float(np.std(residuals))

        lower = forecast_value - 1.28 * std
        upper = forecast_value + 1.28 * std

        return ForecastResult(
            status='ok',
            predicted_profit=Decimal(str(round(forecast_value, 2))),
            lower=Decimal(str(round(lower, 2))),
            upper=Decimal(str(round(upper, 2))),
            algorithm='linear_regression_profit_trend',
            used_months=len(history),
        )

    @staticmethod
    def as_dict(result: ForecastResult) -> Dict[str, Any]:
        return {
            'status': result.status,
            'predicted_profit': str(result.predicted_profit) if result.predicted_profit is not None else None,
            'lower': str(result.lower) if result.lower is not None else None,
            'upper': str(result.upper) if result.upper is not None else None,
            'algorithm': result.algorithm,
            'used_months': result.used_months,
        }
