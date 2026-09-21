FROM python:3.12-slim

WORKDIR /app

# Install OS dependencies needed by sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the FastAPI source code (flattened into /app/app)
COPY backend/app/ ./app/

EXPOSE 8000

# Run uvicorn pointing at the correct module path
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
