"""Customer Domain — Domain Services (pure business logic, no infrastructure)."""

from services.customer.domain.model.customer import Customer
from services.customer.domain.model.value_objects import CustomerSegment


class CustomerSegmentationService:
    """Determines customer segment based on CLV and behavior metrics."""

    @staticmethod
    def calculate_segment(clv_score: float, months_active: int) -> CustomerSegment:
        """Pure business rule — no external dependencies."""
        if clv_score >= 800 and months_active >= 24:
            return CustomerSegment.PLATINUM
        elif clv_score >= 500 and months_active >= 12:
            return CustomerSegment.GOLD
        elif clv_score >= 200 and months_active >= 6:
            return CustomerSegment.SILVER
        elif months_active < 3:
            return CustomerSegment.NEW
        else:
            return CustomerSegment.BRONZE

    @staticmethod
    def assess_churn_risk(customer: Customer, complaint_count: int, days_since_last_usage: int) -> float:
        """Simple churn risk score (0.0 - 1.0). Will be replaced by ML model later."""
        risk = 0.0

        if complaint_count >= 3:
            risk += 0.3
        elif complaint_count >= 1:
            risk += 0.1

        if days_since_last_usage >= 30:
            risk += 0.4
        elif days_since_last_usage >= 14:
            risk += 0.2

        if customer.segment == CustomerSegment.CHURNING:
            risk += 0.2

        return min(risk, 1.0)
