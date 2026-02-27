"""Mock data seeder — populates DB with realistic fake telecom data.

Uses Faker to generate Turkish telecom customer profiles, invoices,
network nodes, and complaints. Run once after docker compose up.

Usage:
    python scripts/seed_mock_data.py
"""

import asyncio
import random
from decimal import Decimal

from faker import Faker

fake = Faker("tr_TR")


# ── Mock customer data ─────────────────────────────────────

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

        customers.append({
            "name": fake.name(),
            "phone_number": f"5{random.randint(30,59)}{fake.numerify('######')}",
            "email": fake.email(),
            "segment": segment,
            "subscription_plan": random.choice(PLANS),
            "clv_score": round(clv, 2),
        })
    return customers


def generate_invoices(customer_ids: list[str], months: int = 3) -> list[dict]:
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
            invoices.append({
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
            })
    return invoices


def generate_complaints(customer_ids: list[str]) -> list[dict]:
    complaints = []
    # ~30% of customers have at least one complaint
    complainers = random.sample(customer_ids, k=int(len(customer_ids) * 0.3))
    for cid in complainers:
        num_complaints = random.randint(1, 3)
        for _ in range(num_complaints):
            complaints.append({
                "customer_id": cid,
                "complaint_type": random.choice(COMPLAINT_TYPES),
                "description": random.choice(MOCK_COMPLAINTS),
                "priority": random.choice(PRIORITIES),
                "status": random.choice(["open", "open", "in_progress", "resolved"]),
            })
    return complaints


def generate_network_nodes(count: int = 20) -> list[dict]:
    cities = ["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya", "Adana", "Konya", "Gaziantep"]
    node_types = ["base_station", "fiber_node", "switch", "router"]
    statuses = ["active", "active", "active", "degraded", "down"]

    nodes = []
    for i in range(count):
        city = random.choice(cities)
        nodes.append({
            "node_id": f"NODE-{city[:3].upper()}-{i:03d}",
            "node_type": random.choice(node_types),
            "city": city,
            "status": random.choice(statuses),
            "latitude": round(random.uniform(36.0, 42.0), 6),
            "longitude": round(random.uniform(26.0, 44.0), 6),
            "connected_customers": random.randint(50, 5000),
        })
    return nodes


async def seed():
    """Main seed function — generates and prints mock data summary."""
    print("Generating mock data...")

    customers = generate_customers(50)
    print(f"  Customers:     {len(customers)}")

    # Use fake UUIDs for demo (real seeding would use actual DB IDs)
    import uuid
    fake_ids = [str(uuid.uuid4()) for _ in customers]

    invoices = generate_invoices(fake_ids, months=3)
    print(f"  Invoices:      {len(invoices)}")

    complaints = generate_complaints(fake_ids)
    print(f"  Complaints:    {len(complaints)}")

    nodes = generate_network_nodes(20)
    print(f"  Network nodes: {len(nodes)}")

    print("\nMock data generation complete.")
    print("To seed the database, integrate with FastAPI startup or run via Alembic seed.")
    print("\nSample customer:")
    import json
    print(json.dumps(customers[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(seed())
