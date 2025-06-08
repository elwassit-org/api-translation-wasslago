#!/bin/bash

# Startup script for Azure Web App Service
echo "Starting Azure Web App Service deployment - $(date)"
echo "Deployment environment: Production"

# Check if we're in Azure Web Apps environment
if [ ! -z "$WEBSITE_SITE_NAME" ]; then
    echo "Running in Azure Web Apps environment: $WEBSITE_SITE_NAME"
    echo "Note: Dependencies should be automatically installed by Azure Web Apps"
else
    echo "Running in local/container environment"
    # Install Python dependencies only in local environment
    echo "Installing Python dependencies..."
    python -m pip install --upgrade pip
    pip install --no-cache-dir -r requirements.txt
fi

# Create necessary directories (Azure Web Apps specific paths)
echo "Creating application directories..."
mkdir -p /tmp/app
mkdir -p ./tmp
mkdir -p ./doc
mkdir -p ./translated
mkdir -p ./models

# Set permissions (limited in Azure Web Apps)
chmod -R 755 ./tmp 2>/dev/null || echo "Note: Limited permissions in Azure Web Apps"
chmod -R 755 ./doc 2>/dev/null || echo "Note: Limited permissions in Azure Web Apps"
chmod -R 755 ./translated 2>/dev/null || echo "Note: Limited permissions in Azure Web Apps"
chmod -R 755 ./models 2>/dev/null || echo "Note: Limited permissions in Azure Web Apps"

# Set environment variables for Azure Web Apps
if [ ! -z "$WEBSITE_SITE_NAME" ]; then
    export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH
    export TEMP=/tmp/app
    export TMP=/tmp/app
else
    export PYTHONPATH=$(pwd):$PYTHONPATH
fi

# Log environment information
echo "Environment variables:"
echo "WEBSITE_SITE_NAME: $WEBSITE_SITE_NAME"
echo "WEBSITE_HOSTNAME: $WEBSITE_HOSTNAME"
echo "PORT: $PORT"
echo "PYTHONPATH: $PYTHONPATH"
echo "TEMP: $TEMP"
echo "Working directory: $(pwd)"

# Check Python and package availability
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"

# Check for PDF processing capabilities
echo "Checking PDF processing capabilities:"
python -c "
try:
    import pdf2image
    print('✓ pdf2image available')
except ImportError:
    print('✗ pdf2image not available')

try:
    import PyPDF2
    print('✓ PyPDF2 available')
except ImportError:
    print('✗ PyPDF2 not available')

try:
    import fitz
    print('✓ PyMuPDF available')
except ImportError:
    print('✗ PyMuPDF not available')
" 2>/dev/null || echo "Could not check Python packages"

# Determine the correct port
LISTEN_PORT=${PORT:-8000}
echo "Will listen on port: $LISTEN_PORT"

# Start the FastAPI application with Gunicorn
echo "Starting FastAPI application..."
exec gunicorn main:app \
    --bind 0.0.0.0:$LISTEN_PORT \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 300 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --capture-output
