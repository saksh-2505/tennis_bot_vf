FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
        pydantic-settings sqlalchemy psycopg2-binary httpx beautifulsoup4 \
        playwright pytest

COPY . .

CMD ["python", "main.py"]
