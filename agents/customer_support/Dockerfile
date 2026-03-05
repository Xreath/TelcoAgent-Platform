FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY shared/ shared/
COPY agents/customer_support/ agents/customer_support/
COPY services/ services/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Expose agent port
EXPOSE 8010

CMD ["uvicorn", "agents.customer_support.main:app", "--host", "0.0.0.0", "--port", "8010"]
