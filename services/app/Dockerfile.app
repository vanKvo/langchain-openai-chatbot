# Dockerfile for business logic (app)
FROM python:3.11-slim

# Install system dependencies required for pymongo
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
EXPOSE 8090

# Wait for MongoDB to be ready before starting the app
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

CMD ["/wait-for-it.sh", "mongodb:27017", "--", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8090"]
