# Aurora FlatSat Simulator - Loopback Testing Guide

## Overview

This document describes the loopback testing system for the Aurora FlatSat Simulator. The simulator supports three devices (ARS, Magnetometer, Reaction Wheel) with RS422 serial loopback testing.

## Hardware Setup

### RS422 Loopback Connections

The physical wiring uses 6 USB-to-RS422 adapters:

| Send Port | Device | Receive Port |
|-----------|--------|--------------|
| ttyUSB0 (Port 1) | ARS | ttyUSB1 (Port 2) |
| ttyUSB2 (Port 3) | Magnetometer | ttyUSB3 (Port 4) |
| ttyUSB4 (Port 5) | Reaction Wheel | ttyUSB5 (Port 6) |

### Wiring Details

- **ARS Loopback**: Connect Port 1 TX to Port 2 RX
- **Magnetometer Loopback**: Connect Port 3 TX to Port 4 RX
- **Reaction Wheel Loopback**: Connect Port 5 TX to Port 6 RX

## Test Scripts

### 1. Diagnostic Test (`diagnostic_serial_test.py`)

Minimal test to verify RS422 hardware is working correctly.

\`\`\`bash
python3 diagnostic_serial_test.py
\`\`\`

This sends a simple byte pattern and verifies it's received correctly. Use this first to confirm hardware connectivity.

### 2. Simple Loopback Test (`simple_loopback_test.py`)

Tests only the ARS device loopback (ttyUSB0 → ttyUSB1) with real ARS packet encoding.

\`\`\`bash
python3 simple_loopback_test.py
\`\`\`

### 3. Complete Loopback Test (`test_all_loopback.py`)

Tests all three devices with their actual packet formats:

\`\`\`bash
python3 test_all_loopback.py
\`\`\`

**What it tests:**
- **ARS**: 12-float data packet with custom encoding
- **Magnetometer**: 3-float magnetic field data (RS485 format)
- **Reaction Wheel**: 4-float telemetry data (Health & Status format)

## Test Data Formats

### ARS (Attitude Reference System)
- **Input**: 12 floats (rate data, position data)
- **Protocol**: Custom serial format
- **Ports**: ttyUSB0 (send) → ttyUSB1 (receive)

### Magnetometer
- **Input**: 3 floats (X, Y, Z magnetic field in nanoTesla)
- **Protocol**: RS485 format per ICD56011974-RS
- **Ports**: ttyUSB2 (send) → ttyUSB3 (receive)

### Reaction Wheel
- **Input**: 4 floats (wheel speed, motor current, temperature, bus voltage)
- **Protocol**: Honeywell format per ICD64020011
- **Ports**: ttyUSB4 (send) → ttyUSB5 (receive)

## Troubleshooting

### No Data Received

1. **Check physical connections**: Verify TX/RX wiring between port pairs
2. **Check USB device names**: Run `ls -l /dev/ttyUSB*` to confirm device mappings
3. **Check permissions**: Ensure user has access with `sudo usermod -a -G dialout $USER`
4. **Test with diagnostic script**: Run `diagnostic_serial_test.py` first

### Permission Denied

\`\`\`bash
sudo chmod 666 /dev/ttyUSB*
# Or add user to dialout group
sudo usermod -a -G dialout $USER
# Then log out and back in
\`\`\`

### Port Already in Use

Make sure no other processes are using the serial ports:

\`\`\`bash
sudo lsof /dev/ttyUSB*
\`\`\`

## Configuration Files

### Full Simulator Config (`config/simulator_config.json`)

Contains all three device configurations with loopback settings:

\`\`\`json
{
  "devices": {
    "ars": {
      "usb_loopback_enabled": true,
      "usb_loopback_send_port": "/dev/ttyUSB0",
      "usb_loopback_receive_port": "/dev/ttyUSB1"
    },
    "magnetometer": {
      "usb_loopback_enabled": true,
      "usb_loopback_send_port": "/dev/ttyUSB2",
      "usb_loopback_receive_port": "/dev/ttyUSB3"
    },
    "reaction_wheel": {
      "usb_loopback_enabled": true,
      "usb_loopback_send_port": "/dev/ttyUSB4",
      "usb_loopback_receive_port": "/dev/ttyUSB5"
    }
  }
}
\`\`\`

### Simple Test Config (`config/simple_loopback_config.json`)

Minimal config for testing only ARS device.

## Running the Full Simulator

After verifying loopback tests pass:

\`\`\`bash
python3 flatsat_device_simulator.py --config config/simulator_config.json
\`\`\`

The simulator will:
1. Connect to MATLAB over TCP/IP
2. Receive sensor data from MATLAB
3. Encode packets for each device
4. Send to hardware (or loopback for testing)
5. Log all packets and performance metrics

## Success Criteria

All tests should show:
- ✅ Sent bytes match received bytes
- ✅ Packet data integrity maintained
- ✅ No timeout or connection errors

Example output:
\`\`\`
✅ ARS LOOPBACK TEST PASSED!
✅ MAGNETOMETER LOOPBACK TEST PASSED!
✅ REACTION WHEEL LOOPBACK TEST PASSED!

🎉 All loopback tests passed!
