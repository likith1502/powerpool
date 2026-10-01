# ==============================================================================
# PowerPool — Container Definition
# Yuva Yodha Energy Tech Hackathon 2026 — Challenge 03: Grid Reliability
# ==============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies (libgomp1 for LightGBM OpenMP support, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for efficient layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code (respects .dockerignore)
COPY . .

# Ensure data directory exists for database mounting
RUN mkdir -p /app/db

# Expose backend (8000) and frontend (8501) ports
EXPOSE 8000 8501

# Default command: FastAPI backend with Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
