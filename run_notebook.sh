#!/bin/bash

# Activate the virtual environment and start Jupyter
echo "🚀 Starting Jupyter notebook with virtual environment..."

# Activate virtual environment
source venv/bin/activate

# Check if jupyter is installed
if ! command -v jupyter &> /dev/null; then
    echo "📦 Installing Jupyter..."
    pip install jupyter notebook
fi

# Start Jupyter notebook
echo "📓 Starting Jupyter notebook..."
echo "🌐 Open your browser to the URL shown below"
echo "📁 The notebook file is: test_urls.ipynb"
echo ""
jupyter notebook test_urls.ipynb 