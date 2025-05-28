#!/bin/bash

# DiarizationScoring Virtual Environment Setup Script
# This script helps you create and manage the Python virtual environment properly

echo "🔧 DiarizationScoring Environment Setup"
echo "======================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8+ and try again"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
echo "🐍 Found Python $PYTHON_VERSION"

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "📁 Virtual environment already exists"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Removing existing virtual environment..."
        rm -rf venv
    else
        echo "ℹ️  Using existing virtual environment"
        echo "To activate: source venv/bin/activate"
        echo "To install/update dependencies: pip install -r requirements.txt"
        exit 0
    fi
fi

# Create virtual environment
echo "🔨 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "⚡ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📥 Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 To get started:"
echo "1. Activate the environment: source venv/bin/activate"
echo "2. Run the application: python main.py"
echo ""
echo "💡 Tips:"
echo "- Always activate the virtual environment before working on the project"
echo "- The venv/ folder is excluded from git (as it should be)"
echo "- If you add new dependencies, update requirements.txt with: pip freeze > requirements.txt"
echo ""
echo "⚠️  IMPORTANT: Never commit the venv/ folder to git!" 