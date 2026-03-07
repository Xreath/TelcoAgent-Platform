"""Tests for Customer Aggregate Root and Value Objects."""

from services.customer.domain.model.customer import Customer
from services.customer.domain.model.events import (
    ComplaintFiled,
    CustomerCreated,
    CustomerSegmentChanged,
)
from services.customer.domain.model.value_objects import (
    Address,
    CustomerSegment,
    PhoneNumber,
    SubscriptionPlan,
)

# ── Customer Factory ─────────────────────────────────────────


class TestCustomerCreate:
    def test_factory_creates_customer(self, sample_phone_number: PhoneNumber):
        customer = Customer.create(
            name="Test User",
            phone_number=sample_phone_number,
        )
        assert customer.name == "Test User"
        assert customer.is_active is True

    def test_factory_raises_created_event(self, sample_phone_number: PhoneNumber):
        customer = Customer.create(
            name="Test User",
            phone_number=sample_phone_number,
        )
        events = customer.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], CustomerCreated)
        assert events[0].name == "Test User"
        assert events[0].event_type == "customer.created"
        assert events[0].aggregate_type == "Customer"

    def test_factory_default_segment_is_new(self, sample_phone_number: PhoneNumber):
        customer = Customer.create(name="Test", phone_number=sample_phone_number)
        assert customer.segment == CustomerSegment.NEW

    def test_factory_default_plan_is_prepaid_basic(self, sample_phone_number: PhoneNumber):
        customer = Customer.create(name="Test", phone_number=sample_phone_number)
        assert customer.subscription_plan == SubscriptionPlan.PREPAID_BASIC

    def test_factory_custom_plan(self, sample_phone_number: PhoneNumber):
        customer = Customer.create(
            name="Test",
            phone_number=sample_phone_number,
            subscription_plan=SubscriptionPlan.POSTPAID_ENTERPRISE,
        )
        assert customer.subscription_plan == SubscriptionPlan.POSTPAID_ENTERPRISE


# ── Segment Change ───────────────────────────────────────────


class TestCustomerSegmentChange:
    def test_change_segment_updates_state(self, sample_customer: Customer):
        sample_customer.collect_events()  # clear factory event
        sample_customer.change_segment(CustomerSegment.GOLD, reason="CLV arttı")
        assert sample_customer.segment == CustomerSegment.GOLD

    def test_change_segment_raises_event(self, sample_customer: Customer):
        sample_customer.collect_events()
        sample_customer.change_segment(CustomerSegment.PLATINUM, reason="VIP upgrade")

        events = sample_customer.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], CustomerSegmentChanged)
        assert events[0].old_segment == "new"
        assert events[0].new_segment == "platinum"
        assert events[0].reason == "VIP upgrade"

    def test_same_segment_no_event(self, sample_customer: Customer):
        """Aynı segmentte kalıyorsa event üretmemeli."""
        sample_customer.collect_events()
        sample_customer.change_segment(CustomerSegment.NEW, reason="Aynı")
        events = sample_customer.collect_events()
        assert len(events) == 0


# ── Complaint ────────────────────────────────────────────────


class TestCustomerComplaint:
    def test_file_complaint_raises_event(self, sample_customer: Customer):
        sample_customer.collect_events()
        sample_customer.file_complaint(
            complaint_type="billing",
            description="Faturada hatalı tutar",
            priority="high",
        )
        events = sample_customer.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], ComplaintFiled)
        assert events[0].complaint_type == "billing"
        assert events[0].priority == "high"

    def test_file_complaint_default_priority(self, sample_customer: Customer):
        sample_customer.collect_events()
        sample_customer.file_complaint(
            complaint_type="network",
            description="Sinyal yok",
        )
        events = sample_customer.collect_events()
        assert events[0].priority == "medium"


# ── Deactivate ───────────────────────────────────────────────


class TestCustomerDeactivate:
    def test_deactivate_sets_inactive(self, sample_customer: Customer):
        assert sample_customer.is_active is True
        sample_customer.deactivate()
        assert sample_customer.is_active is False


# ── Value Objects ────────────────────────────────────────────


class TestPhoneNumber:
    def test_full_number(self):
        pn = PhoneNumber(country_code="+90", number="5551234567")
        assert pn.full_number == "+905551234567"

    def test_str(self):
        pn = PhoneNumber(number="5559876543")
        assert str(pn) == "+905559876543"

    def test_frozen(self):
        pn = PhoneNumber(number="5551111111")
        try:
            pn.number = "changed"
            assert False, "Should be frozen"
        except Exception:
            pass


class TestAddress:
    def test_fields(self, sample_address: Address):
        assert sample_address.city == "Istanbul"
        assert sample_address.district == "Kadikoy"

    def test_frozen(self, sample_address: Address):
        try:
            sample_address.city = "Ankara"
            assert False, "Should be frozen"
        except Exception:
            pass


class TestSubscriptionPlan:
    def test_enum_values(self):
        assert SubscriptionPlan.PREPAID_BASIC == "prepaid_basic"
        assert SubscriptionPlan.POSTPAID_ENTERPRISE == "postpaid_enterprise"
        assert SubscriptionPlan.FIBER_HOME == "fiber_home"
