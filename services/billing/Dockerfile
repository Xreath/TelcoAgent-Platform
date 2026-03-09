FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# ── Layer 1: Install dependencies (cached unless pyproject.toml changes) ──
COPY pyproject.toml .
# Create stub packages so pip can resolve the editable install
RUN mkdir -p services/customer services/billing agents shared && \
    pip install --no-cache-dir -e .

# ── Layer 2: Copy source code (changes frequently, doesn't retrigger pip) ──
COPY shared/ shared/
COPY services/billing/ services/billing/
COPY services/customer/ services/customer/
COPY alembic/ alembic/
COPY alembic.ini .

EXPOSE 8002

# Run migrations then start the server
CMD alembic upgrade head && uvicorn services.billing.api.main:app --host 0.0.0.0 --port 8002
