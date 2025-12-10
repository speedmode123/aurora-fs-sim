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
    """Create a simple test packet - just a recognizable pattern"""
    test_packet = bytes([
        0xAA,  # Sync byte
        0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
        0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10
    ])
    return test_packet

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
            logger.info("Waiting for monitoring thread to stabilize...")
            time.sleep(1.0)
            
            # Run test
            logger.info("Sending packet...")
            result = tester.test_device_packet('ars', test_packet)
            
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
                logger.error(f"Received: {result.received_bytes.hex().upper() if result.received_bytes else '(none)'}")
                logger.error(f"Error:    {result.error_message}")
                logger.error("")
                logger.error("Troubleshooting steps:")
                logger.error("  1. Verify physical connection: TX0 -> RX1")
                logger.error("  2. Check port permissions: ls -l /dev/ttyUSB*")
                logger.error("  3. Verify baud rate matches hardware")
                logger.error("  4. Try with different data patterns")
            
            logger.info("")
            
        except KeyboardInterrupt:
            logger.info("\nTest interrupted by user")
        except Exception as e:
            logger.error(f"Test error: {e}")
            import traceback
            traceback.print_exc()
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
