# FastAPI Backend Docker Container Blueprint for AWS App Runner / AWS ECS
FROM python:3.11-slim

WORKDIR /app

# Ensure Python output is sent directly to terminal/logs without buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Pre-install lightweight CPU-only PyTorch (~150MB instead of 2.5GB CUDA) with layer caching
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install runtime python packages (excluding dev/test tools in production)
COPY requirements.txt .
RUN grep -vE "^(ruff|black|bandit|pre-commit|pytest)" requirements.txt > req-prod.txt && \
    pip install --no-cache-dir -r req-prod.txt && \
    rm req-prod.txt

# Copy backend application code
COPY app/ app/

EXPOSE 8000

# Run FastAPI app using Uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
