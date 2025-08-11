#!/bin/bash
# Cross-platform virtual environment activation script for Linux/macOS
# Usage: source backend/activate.sh

# Change to backend directory if not already there
if [ ! -f "activate.sh" ]; then
    echo "Navigating to backend directory..."
    cd "$(dirname "$0")"
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found at .venv"
    echo "💡 Run: uv venv --python python3"
    echo "💡 Then: uv pip install -r requirements.txt"
    return 1
fi

# Activate the virtual environment
echo "🐍 Activating Python virtual environment..."
source .venv/bin/activate

# Verify activation
if [ "$VIRTUAL_ENV" != "" ]; then
    echo "✅ Virtual environment activated: $VIRTUAL_ENV"
    echo "🔗 Python version: $(python --version)"
    echo "📦 pip path: $(which pip)"
    echo ""
    echo "🚀 Ready to run Python commands!"
    echo "💡 Tip: Use 'deactivate' to exit the virtual environment"
else
    echo "❌ Failed to activate virtual environment"
    return 1
fi