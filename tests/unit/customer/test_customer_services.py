"""Tests for CustomerSegmentationService — pure business rules."""

import pytest

from services.customer.domain.model.customer import Customer
from services.customer.domain.model.value_objects import CustomerSegment, PhoneNumber
from services.customer.domain.services import CustomerSegmentationService

# ── calculate_segment ────────────────────────────────────────


class TestCalculateSegment:
    def test_platinum_high_clv_long_tenure(self):
        result = CustomerSegmentationService.calculate_segment(clv_score=900, months_active=36)
        assert result == CustomerSegment.PLATINUM

    def test_platinum_boundary(self):
        result = CustomerSegmentationService.calculate_segment(clv_score=800, months_active=24)
        assert result == CustomerSegment.PLATINUM

    def test_gold(self):
        result = CustomerSegmentationService.calculate_segment(clv_score=600, months_active=18)
        assert result == CustomerSegment.GOLD

    def test_gold_boundary(self):
        result = CustomerSegmentationService.calculate_segment(clv_score=500, months_active=12)
        assert result == CustomerSegment.GOLD

    def test_silver(self):
        result = CustomerSegmentationService.calculate_segment(clv_score=300, months_active=8)
        assert result == CustomerSegment.SILVER

    def test_silver_boundary(self):
        result = CustomerSegmentationService.calculate_segment(clv_score=200, months_active=6)
        assert result == CustomerSegment.SILVER

    def test_new_customer(self):
        result = CustomerSegmentationService.calculate_segment(clv_score=50, months_active=1)
        assert result == CustomerSegment.NEW

    def test_bronze_fallback(self):
        """CLV düşük ama 3+ ay aktif → BRONZE."""
        result = CustomerSegmentationService.calculate_segment(clv_score=100, months_active=6)
        assert result == CustomerSegment.BRONZE


# ── assess_churn_risk ────────────────────────────────────────


class TestAssessChurnRisk:
    @pytest.fixture
    def base_customer(self) -> Customer:
        return Customer.create(name="Test", phone_number=PhoneNumber(number="5550000000"))

    def test_zero_risk_baseline(self, base_customer: Customer):
        risk = CustomerSegmentationService.assess_churn_risk(
            customer=base_customer,
            complaint_count=0,
            days_since_last_usage=0,
        )
        assert risk == 0.0

    def test_high_complaint_count(self, base_customer: Customer):
        risk = CustomerSegmentationService.assess_churn_risk(
            customer=base_customer,
            complaint_count=5,
            days_since_last_usage=0,
        )
        assert risk == pytest.approx(0.3)

    def test_moderate_complaint_count(self, base_customer: Customer):
        risk = CustomerSegmentationService.assess_churn_risk(
            customer=base_customer,
            complaint_count=2,
            days_since_last_usage=0,
        )
        assert risk == pytest.approx(0.1)

    def test_long_inactivity(self, base_customer: Customer):
        risk = CustomerSegmentationService.assess_churn_risk(
            customer=base_customer,
            complaint_count=0,
            days_since_last_usage=45,
        )
        assert risk == pytest.approx(0.4)

    def test_moderate_inactivity(self, base_customer: Customer):
        risk = CustomerSegmentationService.assess_churn_risk(
            customer=base_customer,
            complaint_count=0,
            days_since_last_usage=20,
        )
        assert risk == pytest.approx(0.2)

    def test_churning_segment_adds_risk(self):
        customer = Customer.create(name="Test", phone_number=PhoneNumber(number="5550000000"))
        customer.segment = CustomerSegment.CHURNING
        risk = CustomerSegmentationService.assess_churn_risk(
            customer=customer,
            complaint_count=0,
            days_since_last_usage=0,
        )
        assert risk == pytest.approx(0.2)

    def test_max_risk_capped_at_1(self):
        """Tüm risk faktörleri birleştiğinde 1.0'ı geçmemeli."""
        customer = Customer.create(name="Test", phone_number=PhoneNumber(number="5550000000"))
        customer.segment = CustomerSegment.CHURNING
        risk = CustomerSegmentationService.assess_churn_risk(
            customer=customer,
            complaint_count=10,  # +0.3
            days_since_last_usage=60,  # +0.4
            # churning: +0.2 → total = 0.9, capped at 1.0
        )
        assert risk <= 1.0
