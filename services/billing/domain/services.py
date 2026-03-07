"""Billing Domain — Pure domain services (no I/O)."""

from decimal import Decimal
from typing import Any

from services.billing.domain.model.value_objects import Money


class BillingAnomalyService:
    """Detects billing anomalies by comparing invoices against historical patterns."""

    ANOMALY_THRESHOLD_PERCENT = 30.0

    @staticmethod
    def detect_anomaly(
        current_amount: Money,
        historical_amounts: list[Money],
    ) -> dict[str, Any]:
        """Compare current invoice against historical average.

        Returns dict with anomaly_detected, deviation_percent, and recommendation.
        """
        if not historical_amounts:
            return {"anomaly_detected": False, "reason": "Insufficient data"}

        avg = sum(m.amount for m in historical_amounts) / Decimal(len(historical_amounts))
        deviation_pct = ((current_amount.amount - avg) / avg) * 100 if avg > 0 else Decimal(0)

        result: dict[str, Any] = {
            "current_amount": str(current_amount.amount),
            "historical_average": str(round(avg, 2)),
            "deviation_percent": float(round(deviation_pct, 2)),
            "anomaly_detected": abs(float(deviation_pct)) > BillingAnomalyService.ANOMALY_THRESHOLD_PERCENT,
        }

        if result["anomaly_detected"]:
            result["recommendation"] = (
                "Faturada anormal sapma tespit edildi. Detayli inceleme ve musteri bilgilendirmesi onerilir."
            )

        return result
