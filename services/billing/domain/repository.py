"""Billing Domain — Abstract Repository Interfaces."""

from abc import ABC, abstractmethod
from uuid import UUID

from services.billing.domain.model.invoice import Invoice


class InvoiceRepository(ABC):
    """Abstract repository — infrastructure layer provides concrete implementation."""

    @abstractmethod
    async def save(self, invoice: Invoice) -> Invoice: ...

    @abstractmethod
    async def find_by_id(self, invoice_id: UUID) -> Invoice | None: ...

    @abstractmethod
    async def find_by_customer(self, customer_id: UUID) -> list[Invoice]: ...

    @abstractmethod
    async def delete(self, invoice_id: UUID) -> bool: ...
