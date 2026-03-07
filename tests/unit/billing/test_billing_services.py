"""Tests for BillingAnomalyService — pure domain service."""

from decimal import Decimal

from services.billing.domain.model.value_objects import Currency, Money
from services.billing.domain.services import BillingAnomalyService


class TestBillingAnomalyService:
    def test_anomaly_detected_high_deviation(self):
        """Mevcut fatura ortalamanın %30'undan fazla sapıyorsa anomali."""
        current = Money(amount=Decimal("300.00"), currency=Currency.TRY)
        historical = [
            Money(amount=Decimal("150.00"), currency=Currency.TRY),
            Money(amount=Decimal("160.00"), currency=Currency.TRY),
            Money(amount=Decimal("155.00"), currency=Currency.TRY),
        ]
        result = BillingAnomalyService.detect_anomaly(current, historical)
        assert result["anomaly_detected"] is True
        assert result["deviation_percent"] > 30.0
        assert "recommendation" in result

    def test_no_anomaly_normal_amount(self):
        """Normal sapma — anomali yok."""
        current = Money(amount=Decimal("165.00"), currency=Currency.TRY)
        historical = [
            Money(amount=Decimal("150.00"), currency=Currency.TRY),
            Money(amount=Decimal("160.00"), currency=Currency.TRY),
            Money(amount=Decimal("155.00"), currency=Currency.TRY),
        ]
        result = BillingAnomalyService.detect_anomaly(current, historical)
        assert result["anomaly_detected"] is False
        assert "recommendation" not in result

    def test_empty_historical_data(self):
        """Tarihçe yoksa yetersiz veri — anomali tespit edilemez."""
        current = Money(amount=Decimal("200.00"), currency=Currency.TRY)
        result = BillingAnomalyService.detect_anomaly(current, [])
        assert result["anomaly_detected"] is False
        assert result["reason"] == "Insufficient data"

    def test_negative_deviation_anomaly(self):
        """Fatura normalden çok düşükse de anomali olmalı."""
        current = Money(amount=Decimal("50.00"), currency=Currency.TRY)
        historical = [
            Money(amount=Decimal("150.00"), currency=Currency.TRY),
            Money(amount=Decimal("160.00"), currency=Currency.TRY),
            Money(amount=Decimal("155.00"), currency=Currency.TRY),
        ]
        result = BillingAnomalyService.detect_anomaly(current, historical)
        assert result["anomaly_detected"] is True
        assert result["deviation_percent"] < -30.0

    def test_result_contains_amounts(self):
        """Sonuç current_amount ve historical_average içermeli."""
        current = Money(amount=Decimal("200.00"), currency=Currency.TRY)
        historical = [Money(amount=Decimal("100.00"), currency=Currency.TRY)]
        result = BillingAnomalyService.detect_anomaly(current, historical)
        assert "current_amount" in result
        assert "historical_average" in result
        assert result["current_amount"] == "200.00"
        assert result["historical_average"] == "100.00"
