FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml .
RUN pip install --no-cache-dir -e . || true

COPY driftguard/ ./driftguard/
COPY finsight/ ./finsight/
COPY scripts/ ./scripts/
COPY demo/ ./demo/

EXPOSE 8080

CMD ["uvicorn", "driftguard.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
