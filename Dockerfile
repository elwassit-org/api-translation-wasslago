# Use Python 3.12 slim image for better performance and smaller size
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    POPPLER_PATH=/usr/bin \
    TEMP_FOLDER=/app/temp \
    DOC_FOLDER=/app/doc \
    SAVE_DIR=/app/translated \
    YOLO_MODEL_PATH=/app/models/yolov11x_best.pt

# Install system dependencies with multiple DNS resolution strategies
RUN apt-get update || (echo "nameserver 8.8.8.8" > /etc/resolv.conf && \
    echo "nameserver 8.8.4.4" >> /etc/resolv.conf && \
    echo "nameserver 1.1.1.1" >> /etc/resolv.conf && \
    apt-get update) && \
    apt-get install -y --no-install-recommends \
        poppler-utils \
        wget \
        ca-certificates \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create app user and directories
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN mkdir -p /app/doc \
             /app/translated \
             /app/temp \
             /app/logs \
             /app/models \
             /app/scripts

# Set work directory
WORKDIR /app

# Copy Docker-optimized requirements first for better Docker layer caching
COPY requirements-docker.txt ./requirements.txt

# Install Python dependencies with extended timeout and retry logic
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --timeout=600 --retries=10 \
    --default-timeout=600 --trusted-host pypi.org --trusted-host pypi.python.org \
    -r requirements.txt

# Copy application code
COPY . .

# Make startup script executable
RUN chmod +x scripts/startup.sh scripts/download_model.py

# Set ownership after copying files
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE $PORT

# Health check optimized for Container Apps
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Start the application with model download
CMD ["./scripts/startup.sh"]
