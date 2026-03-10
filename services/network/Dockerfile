FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN mkdir -p services/network shared && \
    pip install --no-cache-dir -e .

COPY shared/ shared/
COPY services/ services/
COPY alembic/ alembic/
COPY alembic.ini .

EXPOSE 8003

CMD alembic upgrade head && uvicorn services.network.api.main:app --host 0.0.0.0 --port 8003
