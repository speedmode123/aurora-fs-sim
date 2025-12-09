# FlatSat Device Simulator - Quick Start Guide

## Installation

```bash
cd /Users/michaelbrooks/Desktop/Astraios/Aurora_FlatSat_v1.0
pip install -r requirements.txt
```

## Quick Test (No MATLAB Required)

### Step 1: Start the Simulator
```bash
python flatsat_device_simulator.py --enable-ars --debug
```

### Step 2: In Another Terminal, Start Test Sender
```bash
python examples/matlab_tcp_sender.py --enable-ars --duration 30
```

You should see:
- **Simulator**: Receiving data, encoding packets, sending to output
- **Test Sender**: Sending floats with 10ms spacing, statistics every 10s

## Configuration

Edit `config/simulator_config.json`:

```json
{
  "devices": {
    "ars": {
      "enabled": true,
      "matlab_ports": [5000, 5001, 5002, 5003, 5004, 5005],
      "duplicate_primary_to_redundant": true,
      "redundant_variation_percent": 0.1,
      "output_mode": "serial",
      "output_config": {
        "port": "/dev/ttyUSB0",
        "baud_rate": 115200
      }
    }
  }
}
```

## Key Features

### Data Duplication (NEW)
MATLAB sends **6 floats** (primary only) → Simulator creates **12 values** (adds redundant with 0.1% variation)

### 10ms Timing (NEW)
Test sender maintains precise 10ms spacing between each 8-byte float, matching MATLAB behavior

## Common Use Cases

### Test ARS Only
```bash
# Simulator
python flatsat_device_simulator.py --enable-ars

# Test Sender
python examples/matlab_tcp_sender.py --enable-ars
```

### Test All Devices
```bash
# Simulator
python flatsat_device_simulator.py --all-devices

# Test Sender
python examples/matlab_tcp_sender.py --all-devices
```

### Test for Specific Duration
```bash
python examples/matlab_tcp_sender.py --enable-ars --duration 60
```

### Test with Big Endian
```bash
python examples/matlab_tcp_sender.py --enable-ars --endianness big
```

## Troubleshooting

### Connection Refused
- Make sure simulator is running first
- Check that both use same port (default: 5000)

### No Data Received
- Check `--enable-ars` flag on test sender
- Verify simulator shows "Connected to..." message
- Use `--debug` flag on simulator for verbose logging

### Serial Port Error
```bash
sudo usermod -a -G dialout $USER
# Then log out and back in
```

## Documentation

- **Complete Guide**: `README_flatsat_simulator.md`
- **Test Sender**: `examples/README_test_sender.md`
- **Implementation Details**: `FLATSAT_SIMULATOR_PLAN.md`
- **Completion Summary**: `IMPLEMENTATION_COMPLETE.md`

## Support

For issues:
1. Check logs in `flatsat_simulator.log`
2. Run with `--debug` flag
3. Review documentation files above
