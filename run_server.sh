#!/bin/bash

# Development server startup script
# This script activates the virtual environment and starts the FastAPI server

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run setup_env.sh first to create the virtual environment."
    exit 1
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows/MINGW64
    source venv/Scripts/activate
else
    # Linux/macOS
    source venv/bin/activate
fi

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found in current directory!"
    exit 1
fi

echo "🚀 Starting FastAPI development server..."
echo "Server will be available at: http://127.0.0.1:8000"
echo "API documentation will be available at: http://127.0.0.1:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
