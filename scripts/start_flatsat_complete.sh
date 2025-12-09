#!/bin/bash
# Aurora FlatSat v1.0 - Complete Installer Startup Script
# This script starts the FlatSat Device Simulator with all devices enabled

echo "🛰️ Aurora FlatSat v1.0 - Complete System Startup"
echo "================================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
python3 -c "import socket, struct, threading, logging, json, time, random, math, can" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Missing required Python packages. Please run: pip install -r requirements.txt"
    exit 1
fi

# Create necessary directories
mkdir -p packet_logs
mkdir -p raw_data_logs

echo "✅ Dependencies verified"
echo "🚀 Starting FlatSat Device Simulator..."

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
echo "To send test data, run: python3 matlab_bridge_sender.py"
echo "To stop the simulator, press Ctrl+C"
