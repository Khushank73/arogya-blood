# Dockerfile for FastAPI backend
FROM python:3.12-slim

# Install system dependencies needed for pg2 / compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend app files
COPY backend/app ./app
COPY Dataset.csv .

# Pre-train machine learning models so they are cached in the image
RUN python -c "from app.ai.availability_model import availability_engine; from app.ai.churn_model import churn_engine; availability_engine.train('Dataset.csv'); churn_engine.train('Dataset.csv')"

# Expose FastAPI port
EXPOSE 8000

ENV PYTHONPATH=/workspace

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
