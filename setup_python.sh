#!/bin/bash

# Python 3.11.7 Setup Script for DiarizationScoring Project
# This script downloads and installs Python 3.11.7 for this project

set -e  # Exit on any error

echo "=========================================="
echo "Python 3.11.7 Setup for DiarizationScoring"
echo "=========================================="
echo

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ Error: This setup script is designed for macOS only."
    echo "Please install Python 3.11.7 manually from https://python.org"
    exit 1
fi

# Check if Python 3.11.7 is already installed
if command -v python3.11 &> /dev/null; then
    PYTHON_VERSION=$(python3.11 --version 2>&1 | grep -o "3\.11\.[0-9]*")
    if [[ "$PYTHON_VERSION" == "3.11.7" ]]; then
        echo "✅ Python 3.11.7 is already installed system-wide!"
        echo "Using existing installation..."
        PYTHON_CMD="python3.11"
    else
        echo "⚠️  Found Python $PYTHON_VERSION, but need 3.11.7"
        echo "Will download and install Python 3.11.7..."
        PYTHON_CMD=""
    fi
else
    echo "📥 Python 3.11.7 not found. Will download and install..."
    PYTHON_CMD=""
fi

# Download and install Python 3.11.7 if needed
if [[ -z "$PYTHON_CMD" ]]; then
    echo "📥 Downloading Python 3.11.7 installer..."
    echo "This may take a few minutes depending on your internet connection."
    
    # Download Python 3.11.7 installer for macOS
    if ! curl -L -o python-3.11.7-macos11.pkg "https://www.python.org/ftp/python/3.11.7/python-3.11.7-macos11.pkg"; then
        echo "❌ Error: Failed to download Python installer."
        echo "Please check your internet connection and try again."
        exit 1
    fi
    
    echo "✅ Download complete!"
    echo
    echo "🔧 Installing Python 3.11.7..."
    echo "You may be prompted for your administrator password."
    
    # Install Python 3.11.7
    if ! sudo installer -pkg python-3.11.7-macos11.pkg -target /; then
        echo "❌ Error: Failed to install Python."
        echo "Please check that you have administrator privileges."
        rm -f python-3.11.7-macos11.pkg
        exit 1
    fi
    
    # Clean up installer
    rm python-3.11.7-macos11.pkg
    echo "✅ Python 3.11.7 installed successfully!"
    
    # Set the Python command
    PYTHON_CMD="python3.11"
fi

echo
echo "🐍 Creating virtual environment..."

# Check if virtual environment already exists
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists. Removing old one..."
    rm -rf venv
fi

# Create virtual environment using Python 3.11.7
if ! $PYTHON_CMD -m venv venv; then
    echo "❌ Error: Failed to create virtual environment."
    echo "Please ensure Python 3.11.7 was installed correctly."
    exit 1
fi

echo "✅ Virtual environment created successfully!"
echo
echo "🎉 Setup Complete!"
echo
echo "Next steps:"
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo
echo "2. Verify Python version:"
echo "   python --version"
echo
echo "3. Install project dependencies:"
echo "   pip install -r requirements.txt"
echo
echo "4. Run the application:"
echo "   python main.py"
echo
echo "Note: The virtual environment uses Python 3.11.7 exclusively."
echo "When you're done working, deactivate with: deactivate"
echo "==========================================" 