import asyncio
import random
import uuid
import sys
import os

from faker import Faker

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.utils.database import engine, Base
from services.customer.infrastructure.orm_models import CustomerORM, ComplaintORM
from services.billing.infrastructure.orm_models import InvoiceORM

fake = Faker("tr_TR")

SEGMENTS = ["platinum", "gold", "silver", "bronze", "new", "churning"]
PLANS = ["prepaid_basic", "prepaid_premium", "postpaid_starter", "postpaid_business", "fiber_home"]
COMPLAINT_TYPES = ["billing", "network", "service", "general"]
PRIORITIES = ["low", "medium", "high", "critical"]

MOCK_COMPLAINTS = [
    "Faturamda beklenmedik bir ücret var, açıklama istiyorum.",
    "İnternet hızım son haftada çok düştü, teknik destek lazım.",
    "Yanlış paket aktivasyonu yapılmış, düzeltilmesini istiyorum.",
    "SMS gönderirken sorun yaşıyorum, iletilmiyor.",
    "Roaming hizmetim aktif değil, yurt dışındayım.",
    "Fatura tutarı geçen aya göre 3 kat arttı, neden?",
    "Hat kaydı hatalı yapılmış, ismim yanlış.",
    "Fiber kurulumu randevusunu kaçırdınız, yeniden gelmiyorsunuz.",
    "Numara taşıma işlemim 5 gündür bekliyor.",
    "Kota bitmiş gösteriyor ama kullanmadım.",
]

def generate_customers(count: int = 50) -> list[dict]:
    customers = []
    for _ in range(count):
        segment = random.choice(SEGMENTS)
        clv = {
            "platinum": random.uniform(800, 1200),
            "gold": random.uniform(500, 799),
            "silver": random.uniform(200, 499),
            "bronze": random.uniform(50, 199),
            "new": random.uniform(0, 49),
            "churning": random.uniform(10, 150),
        }[segment]

        customers.append(
            {
                "id": uuid.uuid4(),
                "name": fake.name(),
                "phone_number": f"5{random.randint(30, 59)}{fake.numerify('######')}",
                "email": fake.email(),
                "segment": segment,
                "subscription_plan": random.choice(PLANS),
                "clv_score": round(clv, 2),
                "is_active": True,
            }
        )
    return customers

def generate_invoices(customer_ids: list[uuid.UUID], months: int = 3) -> list[dict]:
    invoices = []
    current_year = 2026
    for cid in customer_ids:
        for month_offset in range(months):
            month = 2 - month_offset
            year = current_year
            if month <= 0:
                month += 12
                year -= 1

            base = random.uniform(50, 500)
            invoices.append(
                {
                    "id": uuid.uuid4(),
                    "customer_id": cid,
                    "period_year": year,
                    "period_month": month,
                    "amount": round(base, 2),
                    "currency": "TRY",
                    "status": random.choice(["paid", "paid", "paid", "issued", "overdue"]),
                    "line_items": [
                        {"description": "Aylık hat bedeli", "amount": str(round(base * 0.3, 2))},
                        {"description": "İnternet paketi", "amount": str(round(base * 0.5, 2))},
                        {"description": "Katma değerli hizmetler", "amount": str(round(base * 0.2, 2))},
                    ],
                }
            )
    return invoices

def generate_complaints(customer_ids: list[uuid.UUID]) -> list[dict]:
    complaints = []
    complainers = random.sample(customer_ids, k=int(len(customer_ids) * 0.3))
    for cid in complainers:
        num_complaints = random.randint(1, 3)
        for _ in range(num_complaints):
            complaints.append(
                {
                    "id": uuid.uuid4(),
                    "customer_id": cid,
                    "complaint_type": random.choice(COMPLAINT_TYPES),
                    "description": random.choice(MOCK_COMPLAINTS),
                    "priority": random.choice(PRIORITIES),
                    "status": random.choice(["open", "open", "in_progress", "resolved"]),
                }
            )
    return complaints

async def seed():
    print("Connecting to database to seed mock data...")

    async with engine.begin() as conn:
        # Create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        # Check if already seeded
        result = await session.execute(select(CustomerORM).limit(1))
        if result.scalar_one_or_none() is not None:
            print("Database already contains data. Skipping seed.")
            return

        print("Generating mock data...")
        customers_data = generate_customers(50)
        customer_orms = [CustomerORM(**c) for c in customers_data]
        session.add_all(customer_orms)
        await session.flush()

        customer_ids = [c.id for c in customer_orms]

        invoices_data = generate_invoices(customer_ids, months=3)
        invoice_orms = [InvoiceORM(**i) for i in invoices_data]
        session.add_all(invoice_orms)

        complaints_data = generate_complaints(customer_ids)
        complaint_orms = [ComplaintORM(**c) for c in complaints_data]
        session.add_all(complaint_orms)

        await session.commit()

        print(f"Data seeded successfully:")
        print(f"  Customers:     {len(customer_orms)}")
        print(f"  Invoices:      {len(invoice_orms)}")
        print(f"  Complaints:    {len(complaint_orms)}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed())
