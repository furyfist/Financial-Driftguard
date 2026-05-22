FROM python:3.12-slim

WORKDIR /app

# Install system deps needed for pandas/scipy/lightgbm builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency manifests first for layer caching
COPY pyproject.toml ./
COPY requirements.txt ./

# Install the package in editable mode with all extras
RUN pip install --no-cache-dir -e ".[llm,tracing,agent,reports]" || \
    pip install --no-cache-dir -e "."

# Copy the rest of the source
COPY driftguard/ ./driftguard/
COPY finsight/ ./finsight/

EXPOSE 8000

CMD ["uvicorn", "driftguard.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
