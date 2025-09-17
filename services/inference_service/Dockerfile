FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Redis
RUN apt-get update && apt-get install -y \
    curl \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/inference_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY shared/ shared/

# Copy service code
COPY services/inference_service/main.py .

# Expose port
EXPOSE 8000

# Create startup script
COPY services/inference_service/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Run Redis and service
CMD ["/app/start.sh"]
