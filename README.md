# Aurora FlatSat v1.0 - Complete Installer

## Overview

This installer provides a complete, self-contained Aurora FlatSat v1.0 satellite simulation system with support for:

- **ARS (Angular Rate Sensor)**: 12 ports (50038-50049)
- **Magnetometer**: 3 ports (50050-50052) 
- **Reaction Wheel**: 4 ports (50053-50056)

## Quick Start

1. **Install the system:**
   ```bash
   ./install.sh
   ```

2. **Choose your startup mode:**

   **Option A: Complete System (Simulator + MATLAB Bridge)**
   ```bash
   ./scripts/start_flatsat_complete.sh
   ```
   Then in another terminal:
   ```bash
   ./scripts/start_matlab_bridge.sh
   ```

   **Option B: Standalone Simulator (for real MATLAB system)**
   ```bash
   ./scripts/start_flatsat_standalone.sh
   ```

## System Architecture

### Data Flow
```
MATLAB System → TCP Ports → FlatSat Simulator → Device Encoders → Output Transmitters
```

### Port Configuration
- **ARS Ports**: 50038-50049 (12 ports)
  - 50038-50043: Angular rates (rad/s)
  - 50044-50049: Angular positions (rad)

- **Magnetometer Ports**: 50050-50052 (3 ports)
  - Magnetic field components (Tesla)

- **Reaction Wheel Ports**: 50053-50056 (4 ports)
  - 50053-50054: Wheel speed (rad/s)
  - 50055-50056: Wheel torque (Nm)

## Files Structure

```
installer_complete/
├── install.sh                          # Main installation script
├── requirements.txt                    # Python dependencies
├── README.md                          # This file
├── QUICKSTART.md                      # Quick start guide
├── config/
│   └── simulator_config.json          # Main configuration
├── device_encoders/                   # Device-specific encoders
│   ├── ars_encoder.py
│   ├── magnetometer_encoder.py
│   └── reaction_wheel_encoder.py
├── output_transmitters/               # Output interfaces
│   ├── tcp_transmitter.py
│   ├── can_transmitter.py
│   └── serial_transmitter.py
├── scripts/                          # Startup scripts
│   ├── start_flatsat_complete.sh     # Complete system
│   ├── start_flatsat_standalone.sh   # Standalone simulator
│   └── start_matlab_bridge.sh        # MATLAB bridge only
├── docs/                             # Documentation
└── examples/                         # Example usage
```

## Configuration

The main configuration file is `config/simulator_config.json`. Key settings:

- **Device Enable/Disable**: Control which devices are active
- **Port Assignments**: Configure TCP port ranges for each device
- **Output Modes**: Choose output interface (serial, CAN, TCP)
- **Logging**: Enable/disable packet and raw data logging

## Logging

The system generates two types of logs:

1. **Packet Logs** (`packet_logs/`):
   - `ars_packets.log`: Device-formatted ARS packets
   - `magnetometer_packets.log`: Device-formatted magnetometer packets
   - `reaction_wheel_packets.log`: Device-formatted reaction wheel packets

2. **Raw Data Logs** (`raw_data_logs/`):
   - `ars_raw_data.log`: Raw TCP data for ARS
   - `magnetometer_raw_data.log`: Raw TCP data for magnetometer
   - `reaction_wheel_raw_data.log`: Raw TCP data for reaction wheel

## Usage Modes

### Mode 1: Complete System Testing
Use this mode for development and testing with simulated MATLAB data:

1. Start the complete system:
   ```bash
   ./scripts/start_flatsat_complete.sh
   ```

2. In another terminal, start the MATLAB bridge:
   ```bash
   ./scripts/start_matlab_bridge.sh
   ```

### Mode 2: Standalone Simulator
Use this mode when you have a real MATLAB system:

1. Start the standalone simulator:
   ```bash
   ./scripts/start_flatsat_standalone.sh
   ```

2. Connect your MATLAB system to the configured ports

## Troubleshooting

### Common Issues

1. **"Connection refused" errors:**
   - Ensure the FlatSat simulator is running before starting the MATLAB bridge
   - Check that the correct ports are configured

2. **Missing dependencies:**
   - Run `pip install -r requirements.txt`
   - Ensure Python 3.8+ is installed

3. **Permission errors:**
   - Run `chmod +x scripts/*.sh`
   - Ensure you have write permissions for log directories

### Verification

To verify the system is working:

1. Check that all packet logs are being populated
2. Verify raw data logs contain realistic values
3. Monitor console output for connection confirmations

## Support

For technical support or questions about Aurora FlatSat v1.0, refer to the main project documentation or contact the development team.

## Version Information

- **Version**: 1.0
- **Last Updated**: October 2025
- **Compatibility**: Python 3.8+, Linux/macOS/Windows