"""Customer Domain — Abstract Repository Interface."""

from abc import ABC, abstractmethod
from uuid import UUID

from services.customer.domain.model.customer import Customer


class CustomerRepository(ABC):
    """Abstract repository — infrastructure layer provides concrete implementation."""

    @abstractmethod
    async def save(self, customer: Customer) -> Customer:
        ...

    @abstractmethod
    async def find_by_id(self, customer_id: UUID) -> Customer | None:
        ...

    @abstractmethod
    async def find_by_phone(self, phone_number: str) -> Customer | None:
        ...

    @abstractmethod
    async def find_all(self, skip: int = 0, limit: int = 100) -> list[Customer]:
        ...

    @abstractmethod
    async def delete(self, customer_id: UUID) -> bool:
        ...
