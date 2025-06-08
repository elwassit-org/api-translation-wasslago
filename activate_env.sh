#!/bin/bash

# Quick activation script for the virtual environment
# Usage: source activate_env.sh

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup_env.sh first."
    return 1
fi

echo "🔄 Activating virtual environment..."
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows/MINGW64
    source venv/Scripts/activate
else
    # Linux/macOS
    source venv/bin/activate
fi

echo "✅ Virtual environment activated!"
echo "To start the API server, run: python -m uvicorn main:app --reload"
