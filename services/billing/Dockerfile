FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY shared/ shared/
COPY services/billing/ services/billing/

RUN pip install --no-cache-dir -e .

EXPOSE 8002

CMD ["uvicorn", "services.billing.api.main:app", "--host", "0.0.0.0", "--port", "8002"]
