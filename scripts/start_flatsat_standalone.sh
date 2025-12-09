#!/bin/bash
# Aurora FlatSat v1.0 - Standalone Simulator Startup Script
# This script starts the FlatSat simulator WITHOUT the MATLAB bridge
# Use this when you have real MATLAB system available

echo "🛰️ Aurora FlatSat v1.0 - Standalone Simulator"
echo "=============================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
python3 -c "import socket, struct, threading, logging, json, time, random, math" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Missing required Python packages. Please run: pip install -r requirements.txt"
    exit 1
fi

# Create necessary directories
mkdir -p packet_logs
mkdir -p raw_data_logs

echo "✅ Dependencies verified"
echo "🚀 Starting FlatSat Device Simulator (Standalone Mode)..."
echo "📡 Waiting for MATLAB data on ports:"
echo "   ARS: 50038-50049"
echo "   Magnetometer: 50050-50052"
echo "   Reaction Wheel: 50053-50056"

# Start the simulator with all devices enabled
python3 flatsat_device_simulator.py \
    --config config/simulator_config.json \
    --enable-ars \
    --enable-mag \
    --enable-rw \
    --debug

echo "✅ FlatSat Device Simulator started successfully!"
echo "📊 Packet logs will be saved to: packet_logs/"
echo "📊 Raw data logs will be saved to: raw_data_logs/"
echo ""
echo "Ready to receive data from MATLAB system!"
echo "To stop the simulator, press Ctrl+C"
