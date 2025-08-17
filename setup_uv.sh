#!/bin/bash

# Setup script for Wikipedia Dead Reference Finder with UV

echo "🚀 Setting up Wikipedia Dead Reference Finder with UV..."

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV is not installed. Please install UV first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "   or visit: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

echo "✅ UV is installed"

# Create virtual environment and install dependencies
echo "📦 Creating virtual environment and installing dependencies..."
uv sync

echo "✅ Setup complete!"
echo ""
echo "🎯 To run the tool:"
echo "   uv run main.py"
echo ""
echo "🔧 To run with specific options:"
echo "   uv run main.py --limit 10 --verbose"
echo ""
echo "🧪 To run tests:"
echo "   uv run main.py --test --verbose"
echo ""
echo "📚 For more options:"
echo "   uv run main.py --help"
