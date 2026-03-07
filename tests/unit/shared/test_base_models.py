"""Tests for shared DDD base classes — ValueObject, Entity, AggregateRoot, DomainEvent."""

from uuid import UUID

from shared.events.base import DomainEvent
from shared.models.base import AggregateRoot, Entity, ValueObject

# ── ValueObject ──────────────────────────────────────────────


class SampleVO(ValueObject):
    x: int
    y: int


class TestValueObject:
    def test_frozen_immutability(self):
        """ValueObject'ler frozen olmalı — field değiştirmeye çalışınca hata."""
        vo = SampleVO(x=1, y=2)
        try:
            vo.x = 99
            assert False, "Should have raised"
        except Exception:
            pass  # ValidationError expected

    def test_equality_by_value(self):
        """Aynı değerli VO'lar eşit olmalı."""
        a = SampleVO(x=1, y=2)
        b = SampleVO(x=1, y=2)
        assert a == b

    def test_inequality(self):
        a = SampleVO(x=1, y=2)
        b = SampleVO(x=1, y=3)
        assert a != b


# ── Entity ───────────────────────────────────────────────────


class TestEntity:
    def test_auto_id_generation(self):
        """Entity oluşturulduğunda otomatik UUID atanmalı."""
        e = Entity()
        assert isinstance(e.id, UUID)

    def test_unique_ids(self):
        """Her entity farklı UUID almalı."""
        e1 = Entity()
        e2 = Entity()
        assert e1.id != e2.id

    def test_timestamps_auto(self):
        """created_at ve updated_at otomatik doldurulmalı."""
        e = Entity()
        assert e.created_at is not None
        assert e.updated_at is not None


# ── AggregateRoot ────────────────────────────────────────────


class SampleEvent(DomainEvent):
    event_type: str = "test.event"
    aggregate_type: str = "Test"
    payload: str = ""


class TestAggregateRoot:
    def test_add_event(self):
        """Event eklenince pending_events'te görünmeli."""
        agg = AggregateRoot()
        event = SampleEvent(aggregate_id=str(agg.id), payload="hello")
        agg.add_event(event)
        assert len(agg.pending_events) == 1
        assert agg.pending_events[0].payload == "hello"

    def test_collect_events_clears(self):
        """collect_events çağrıldığında event listesi temizlenmeli."""
        agg = AggregateRoot()
        agg.add_event(SampleEvent(aggregate_id=str(agg.id)))
        agg.add_event(SampleEvent(aggregate_id=str(agg.id)))

        collected = agg.collect_events()
        assert len(collected) == 2
        assert len(agg.pending_events) == 0

    def test_pending_events_returns_copy(self):
        """pending_events kopya döndürmeli — dış modifikasyonu engellemek için."""
        agg = AggregateRoot()
        agg.add_event(SampleEvent(aggregate_id=str(agg.id)))

        events = agg.pending_events
        events.clear()  # Dışarıdaki listeyi temizle
        assert len(agg.pending_events) == 1  # İçerideki etkilenmemeli

    def test_no_shared_state_between_instances(self):
        """İki AggregateRoot aynı event listesini paylaşmamalı (C1 bug fix doğrulaması)."""
        agg1 = AggregateRoot()
        agg2 = AggregateRoot()
        agg1.add_event(SampleEvent(aggregate_id=str(agg1.id)))

        assert len(agg1.pending_events) == 1
        assert len(agg2.pending_events) == 0


# ── DomainEvent ──────────────────────────────────────────────


class TestDomainEvent:
    def test_event_id_auto(self):
        """Her event benzersiz event_id almalı."""
        e1 = SampleEvent(aggregate_id="agg-1")
        e2 = SampleEvent(aggregate_id="agg-2")
        assert isinstance(e1.event_id, UUID)
        assert e1.event_id != e2.event_id

    def test_occurred_at_auto(self):
        """occurred_at otomatik doldurulmalı."""
        e = SampleEvent(aggregate_id="agg-1")
        assert e.occurred_at is not None

    def test_frozen(self):
        """DomainEvent immutable olmalı."""
        e = SampleEvent(aggregate_id="agg-1")
        try:
            e.aggregate_id = "changed"
            assert False, "Should have raised"
        except Exception:
            pass
