# Simple Loopback Test

Quick test for validating your ttyUSB0→ttyUSB1 loopback connection.

## Prerequisites

1. **Physical wiring:** RS422 cable connecting Port 1 (ttyUSB0) to Port 2 (ttyUSB1)
2. **Permissions:** Your user must have access to serial ports
   \`\`\`bash
   sudo usermod -a -G dialout $USER
   # Log out and back in for changes to take effect
   \`\`\`

## Running the Test

\`\`\`bash
python3 simple_loopback_test.py
\`\`\`

## What it Tests

- Sends a 62-byte ARS test packet from ttyUSB0
- Receives the same packet on ttyUSB1
- Verifies the data matches exactly
- Measures loopback latency

## Expected Output

\`\`\`
Simple USB Loopback Test - Single Port Pair
Physical wiring:
  ttyUSB0 (Port 1) -> ttyUSB1 (Port 2)

Test Results:
Status: PASS ✓
Latency: 1.23 ms
\`\`\`

## Alternative: Use Simple Config

Run the full simulator with only ARS enabled:

\`\`\`bash
python3 flatsat_device_simulator.py --config config/simple_loopback_config.json
\`\`\`

This disables magnetometer and reaction wheel, focusing only on your working ttyUSB0→ttyUSB1 connection.
