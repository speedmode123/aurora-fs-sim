#!/bin/bash
# Aurora FlatSat v1.0 - Complete Installation Script
# This script installs and configures the complete FlatSat simulator system

echo "🛰️ Aurora FlatSat v1.0 - Complete Installation"
echo "=============================================="

# Get the directory where this script is located
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "📁 Installation directory: $INSTALL_DIR"

# Check if Python 3 is installed
echo "🐍 Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "   Please install Python 3.8 or later and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "✅ Python $PYTHON_VERSION found"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed."
    echo "   Please install pip3 and try again."
    exit 1
fi

echo "✅ pip3 found"

# Install Python dependencies
#echo "📦 Installing Python dependencies..."
#if [ -f "requirements.txt" ]; then
#    pip3 install -r requirements.txt
#    if [ $? -eq 0 ]; then
#        echo "✅ Dependencies installed successfully"
#    else
#        echo "❌ Failed to install dependencies"
#        exit 1
#    fi
#else
#    echo "⚠️  requirements.txt not found, skipping dependency installation"
#fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p packet_logs
mkdir -p raw_data_logs
mkdir -p logs
echo "✅ Directories created"

# Set up permissions
echo "🔐 Setting up permissions..."
chmod +x scripts/*.sh
echo "✅ Scripts made executable"

# Verify installation
echo "🔍 Verifying installation..."
python3 -c "
import sys
import importlib

required_modules = [
    'socket', 'struct', 'threading', 'logging', 
    'json', 'time', 'random', 'math', 'datetime'
]

missing_modules = []
for module in required_modules:
    try:
        importlib.import_module(module)
    except ImportError:
        missing_modules.append(module)

if missing_modules:
    print(f'❌ Missing modules: {missing_modules}')
    sys.exit(1)
else:
    print('✅ All required modules available')
"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Installation completed successfully!"
    echo ""
    echo "📋 Available startup options:"
    echo "   1. Complete system (simulator + MATLAB bridge):"
    echo "      ./scripts/start_flatsat_complete.sh"
    echo ""
    echo "   2. Standalone simulator (for real MATLAB system):"
    echo "      ./scripts/start_flatsat_standalone.sh"
    echo ""
    echo "   3. MATLAB bridge only (if simulator already running):"
    echo "      ./scripts/start_matlab_bridge.sh"
    echo ""
    echo "📊 Log files will be saved to:"
    echo "   - packet_logs/ (device-formatted packets)"
    echo "   - raw_data_logs/ (raw TCP data)"
    echo ""
    echo "🔧 Configuration file: config/simulator_config.json"
    echo ""
    echo "Ready to launch Aurora FlatSat v1.0! 🚀"
else
    echo "❌ Installation verification failed"
    exit 1
fi
