#!/usr/bin/env python3
"""
USB Loopback Test Demo

Demonstrates USB loopback testing for all three devices.
This script shows how to send packets to USB ports and monitor loopback data.
"""

import time
import logging
from usb_loopback_tester import USBLoopbackTester, USBPortConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_packets():
    """Create test packets for each device"""
    
    # ARS test packet (Honeywell format)
    ars_packet = bytes([
        0x55, 0x55,  # Sync bytes
        0x00, 0x01,  # Message counter
        0x00, 0x00, 0x00, 0x00,  # Prime X (32-bit float)
        0x00, 0x00, 0x00, 0x00,  # Prime Y
        0x00, 0x00, 0x00, 0x00,  # Prime Z
        0x00, 0x00, 0x00, 0x00,  # Redundant X
        0x00, 0x00, 0x00, 0x00,  # Redundant Y
        0x00, 0x00, 0x00, 0x00,  # Redundant Z
        0x00, 0x00, 0x00, 0x00,  # Summed Prime X
        0x00, 0x00, 0x00, 0x00,  # Summed Prime Y
        0x00, 0x00, 0x00, 0x00,  # Summed Prime Z
        0x00, 0x00, 0x00, 0x00,  # Summed Redundant X
        0x00, 0x00, 0x00, 0x00,  # Summed Redundant Y
        0x00, 0x00, 0x00, 0x00,  # Summed Redundant Z
        0x00, 0x00,  # Status Word 1
        0x00, 0x00,  # Status Word 2
        0x00, 0x00,  # Status Word 3
        0x00, 0x00   # CRC-16
    ])
    
    # Magnetometer test packet (CAN format)
    mag_packet = bytes([
        0x01,  # Message type (MAGDATA)
        0x00, 0x00, 0x00, 0x00,  # X field (32-bit float)
        0x00, 0x00, 0x00, 0x00,  # Y field
        0x00, 0x00, 0x00, 0x00,  # Z field
        0x00, 0x00, 0x00, 0x00,  # Temperature
        0x00, 0x00, 0x00, 0x00,  # Timestamp
        0x00, 0x00, 0x00, 0x00   # CRC
    ])
    
    # Reaction Wheel test packet (TCP format)
    rw_packet = bytes([
        0x15,  # Telemetry type (HEALTH_STATUS)
        0x00, 0x00, 0x00, 0x00,  # Wheel speed (32-bit float)
        0x00, 0x00, 0x00, 0x00,  # Motor current
        0x00, 0x00, 0x00, 0x00,  # Temperature
        0x00, 0x00, 0x00, 0x00,  # Bus voltage
        0x00, 0x00, 0x00, 0x00,  # Power consumption
        0x00, 0x00, 0x00, 0x00,  # Timestamp
        0x00, 0x00, 0x00, 0x00   # CRC
    ])
    
    return {
        'ars': ars_packet,
        'magnetometer': mag_packet,
        'reaction_wheel': rw_packet
    }

def main():
    """Main test function"""
    
    # Port 1 (ttyUSB0) sends -> Port 2 (ttyUSB1) receives
    # Port 3 (ttyUSB2) sends -> Port 4 (ttyUSB3) receives
    # Port 5 (ttyUSB4) sends -> Port 6 (ttyUSB5) receives
    device_configs = {
        'ars': USBPortConfig(
            send_port='/dev/ttyUSB0',
            receive_port='/dev/ttyUSB1',
            baud_rate=115200
        ),
        'magnetometer': USBPortConfig(
            send_port='/dev/ttyUSB2',
            receive_port='/dev/ttyUSB3',
            baud_rate=115200
        ),
        'reaction_wheel': USBPortConfig(
            send_port='/dev/ttyUSB4',
            receive_port='/dev/ttyUSB5',
            baud_rate=115200
        )
    }
    
    # Create test packets
    test_packets = create_test_packets()
    
    # Create USB loopback tester
    tester = USBLoopbackTester(device_configs)
    
    logger.info("Starting USB Loopback Test Demo")
    logger.info("Physical loopback wiring:")
    logger.info("  ARS: /dev/ttyUSB0 (port 1, send) -> /dev/ttyUSB1 (port 2, receive)")
    logger.info("  Magnetometer: /dev/ttyUSB2 (port 3, send) -> /dev/ttyUSB3 (port 4, receive)")
    logger.info("  Reaction Wheel: /dev/ttyUSB4 (port 5, send) -> /dev/ttyUSB5 (port 6, receive)")
    
    if tester.start_testing():
        try:
            logger.info("Waiting for monitoring threads to stabilize...")
            time.sleep(2)
            
            # Test each device
            logger.info("Testing all devices...")
            results = tester.test_all_devices(test_packets)
            
            # Print results
            logger.info("=== Test Results ===")
            for device_name, result in results.items():
                status = "PASS" if result.success else "FAIL"
                logger.info(f"{device_name.upper()}: {status}")
                logger.info(f"  Sent:    {result.sent_bytes.hex().upper()}")
                logger.info(f"  Received: {result.received_bytes.hex().upper()}")
                logger.info(f"  Latency:  {result.latency_ms:.2f}ms")
                logger.info("")
            
            # Print summary
            tester.print_test_summary()
            
        finally:
            tester.stop_testing()
    else:
        logger.error("Failed to start USB Loopback Test System")
        logger.error("Make sure USB ports are available and loopback cables are connected")

if __name__ == '__main__':
    main()
