# FastAPI Backend Docker Container Blueprint for AWS App Runner / AWS ECS
FROM python:3.11-slim

WORKDIR /app

# Ensure Python output is sent directly to terminal/logs without buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY app/ app/

EXPOSE 8000

# Run FastAPI app using Uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
