#!/usr/bin/env python3
"""
Simple USB Loopback Test - Single Port Pair

Tests only ttyUSB0 (send) -> ttyUSB1 (receive) loopback connection.
Perfect for validating basic RS422 wiring with minimal setup.
"""

import time
import logging
from usb_loopback_tester import USBLoopbackTester, USBPortConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_simple_test_packet():
    """Create a simple test packet for ARS device"""
    # Simple ARS-format packet with recognizable pattern
    ars_packet = bytes([
        0x55, 0x55,  # Sync bytes
        0x00, 0x01,  # Message counter
        0x3F, 0x80, 0x00, 0x00,  # Prime X = 1.0 (float)
        0x40, 0x00, 0x00, 0x00,  # Prime Y = 2.0
        0x40, 0x40, 0x00, 0x00,  # Prime Z = 3.0
        0x3F, 0x80, 0x00, 0x00,  # Redundant X = 1.0
        0x40, 0x00, 0x00, 0x00,  # Redundant Y = 2.0
        0x40, 0x40, 0x00, 0x00,  # Redundant Z = 3.0
        0x00, 0x00, 0x00, 0x00,  # Summed Prime X
        0x00, 0x00, 0x00, 0x00,  # Summed Prime Y
        0x00, 0x00, 0x00, 0x00,  # Summed Prime Z
        0x00, 0x00, 0x00, 0x00,  # Summed Redundant X
        0x00, 0x00, 0x00, 0x00,  # Summed Redundant Y
        0x00, 0x00, 0x00, 0x00,  # Summed Redundant Z
        0x00, 0x01,  # Status Word 1
        0x00, 0x02,  # Status Word 2
        0x00, 0x03,  # Status Word 3
        0xAB, 0xCD   # CRC-16 placeholder
    ])
    
    return ars_packet

def main():
    """Run simple loopback test"""
    
    logger.info("=" * 60)
    logger.info("Simple USB Loopback Test - Single Port Pair")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Physical wiring:")
    logger.info("  ttyUSB0 (Port 1) -> ttyUSB1 (Port 2)")
    logger.info("  Sender: /dev/ttyUSB0")
    logger.info("  Receiver: /dev/ttyUSB1")
    logger.info("")
    
    # Configure only the ARS device with ttyUSB0->ttyUSB1
    device_configs = {
        'ars': USBPortConfig(
            send_port='/dev/ttyUSB0',
            receive_port='/dev/ttyUSB1',
            baud_rate=115200
        )
    }
    
    # Create test packet
    test_packet = create_simple_test_packet()
    logger.info(f"Test packet: {len(test_packet)} bytes")
    logger.info(f"  Hex: {test_packet.hex().upper()}")
    logger.info("")
    
    # Create tester
    tester = USBLoopbackTester(device_configs)
    
    # Start testing
    logger.info("Starting loopback test...")
    if tester.start_testing():
        try:
            # Wait for ports to stabilize
            time.sleep(0.5)
            
            # Run test
            logger.info("Sending packet...")
            result = tester.test_device('ars', test_packet)
            
            # Display results
            logger.info("")
            logger.info("=" * 60)
            logger.info("Test Results")
            logger.info("=" * 60)
            
            if result.success:
                logger.info("Status: PASS ✓")
                logger.info(f"Sent:     {result.sent_bytes.hex().upper()}")
                logger.info(f"Received: {result.received_bytes.hex().upper()}")
                logger.info(f"Latency:  {result.latency_ms:.2f} ms")
                logger.info(f"Match:    {'Yes' if result.sent_bytes == result.received_bytes else 'No'}")
            else:
                logger.error("Status: FAIL ✗")
                logger.error(f"Sent:     {result.sent_bytes.hex().upper()}")
                logger.error(f"Received: {result.received_bytes.hex().upper()}")
                logger.error(f"Error:    {result.error_message}")
            
            logger.info("")
            
        except KeyboardInterrupt:
            logger.info("\nTest interrupted by user")
        except Exception as e:
            logger.error(f"Test error: {e}")
        finally:
            tester.stop_testing()
            logger.info("Test complete")
    else:
        logger.error("Failed to start loopback test")
        logger.error("Check that:")
        logger.error("  1. /dev/ttyUSB0 and /dev/ttyUSB1 exist")
        logger.error("  2. You have permissions (try: sudo usermod -a -G dialout $USER)")
        logger.error("  3. No other program is using these ports")
        logger.error("  4. Physical loopback cable is connected")

if __name__ == '__main__':
    main()
