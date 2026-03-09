import asyncio
import json
import uuid
from aiokafka import AIOKafkaProducer

async def send_complaint_event():
    producer = AIOKafkaProducer(
        bootstrap_servers="localhost:9092",
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    
    try:
        event = {
            "customer_id": "613a0ac0-6699-4f1f-8a22-065896f948ea",
            "complaint_id": str(uuid.uuid4()),
            "complaint_type": "billing",
            "description": "Faturamda aciklanmayan ucret var.",
            "priority": "high",
            "timestamp": "2026-03-09T10:00:00Z"
        }
        print(f"Sending event: {event}")
        await producer.send_and_wait("telco.complaints.filed", event)
        print("Event sent successfully.")
    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(send_complaint_event())
