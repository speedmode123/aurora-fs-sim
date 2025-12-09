#!/bin/bash
# Aurora FlatSat v1.0 - MATLAB Bridge Sender Startup Script
# This script starts the MATLAB bridge sender to simulate MATLAB data

echo "🛰️ Aurora FlatSat v1.0 - MATLAB Bridge Sender"
echo "=============================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if FlatSat simulator is running
echo "🔍 Checking if FlatSat simulator is running..."
if ! pgrep -f "flatsat_device_simulator" > /dev/null; then
    echo "⚠️  FlatSat simulator is not running!"
    echo "   Please start it first with: ./scripts/start_flatsat_complete.sh"
    exit 1
fi

echo "✅ FlatSat simulator is running"
echo "🚀 Starting MATLAB Bridge Sender..."

# Start the MATLAB bridge sender
python3 matlab_bridge_sender.py

echo "✅ MATLAB Bridge Sender completed!"
