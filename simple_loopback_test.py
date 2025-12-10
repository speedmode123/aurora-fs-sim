#!/usr/bin/env python3
"""
Simple USB Loopback Test - Direct Serial Communication

Tests ttyUSB0 (send) -> ttyUSB1 (receive) using the same approach as
the diagnostic script that works. No threads, no queues, just direct serial I/O.
"""

import serial
import time
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_simple_test_packet():
    """Create a simple test packet - just a recognizable pattern"""
    return bytes([
        0xAA,  # Sync byte
        0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
        0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10
    ])

def test_simple_loopback():
    """Test serial loopback with minimal code matching diagnostic_serial_test.py"""
    
    logger.info("=" * 70)
    logger.info("Simple USB Loopback Test - Direct Serial Communication")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Physical wiring:")
    logger.info("  ttyUSB0 (TX) -> ttyUSB1 (RX)")
    logger.info("")
    
    # Create test packet
    test_packet = create_simple_test_packet()
    logger.info(f"Test packet: {len(test_packet)} bytes")
    logger.info(f"  Hex: {test_packet.hex().upper()}")
    logger.info("")
    
    try:
        # Open both ports - exactly like diagnostic script
        logger.info("Opening serial ports...")
        sender = serial.Serial(
            port='/dev/ttyUSB0',
            baudrate=115200,
            bytesize=8,
            stopbits=1,
            parity='N',
            timeout=1.0,
            write_timeout=1.0
        )
        logger.info(f"  ✓ Opened {sender.port} for sending")
        
        receiver = serial.Serial(
            port='/dev/ttyUSB1',
            baudrate=115200,
            bytesize=8,
            stopbits=1,
            parity='N',
            timeout=2.0
        )
        logger.info(f"  ✓ Opened {receiver.port} for receiving")
        logger.info("")
        
        # Clear any existing data
        receiver.reset_input_buffer()
        sender.reset_output_buffer()
        time.sleep(0.1)
        
        # Send data
        logger.info(f"Sending {len(test_packet)} bytes...")
        start_time = time.time()
        bytes_written = sender.write(test_packet)
        sender.flush()
        logger.info(f"  ✓ Wrote {bytes_written} bytes to {sender.port}")
        logger.info("")
        
        # Small delay for data to propagate
        time.sleep(0.5)
        
        # Check what's available
        waiting = receiver.in_waiting
        logger.info(f"Bytes waiting in receive buffer: {waiting}")
        logger.info("")
        
        # Read data
        logger.info("Reading data...")
        received = receiver.read(len(test_packet))
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        logger.info(f"  ✓ Read {len(received)} bytes from {receiver.port}")
        
        if received:
            logger.info(f"  Received: {received.hex().upper()}")
            logger.info("")
            
            # Display results
            logger.info("=" * 70)
            logger.info("Test Results")
            logger.info("=" * 70)
            logger.info(f"Sent:     {test_packet.hex().upper()}")
            logger.info(f"Received: {received.hex().upper()}")
            logger.info(f"Latency:  {latency_ms:.2f} ms")
            
            # Compare
            if received == test_packet:
                logger.info("Match:    Yes")
                logger.info("")
                logger.info("✓ SUCCESS - Loopback test passed!")
                return_code = 0
            else:
                logger.error("Match:    No")
                logger.error("")
                logger.error("✗ FAIL - Data mismatch")
                return_code = 1
        else:
            logger.info("")
            logger.error("=" * 70)
            logger.error("✗ FAIL - No data received")
            logger.error("=" * 70)
            logger.error("")
            logger.error("Troubleshooting:")
            logger.error("  1. Check physical wiring:")
            logger.error("     - TX pin of ttyUSB0 connected to RX pin of ttyUSB1")
            logger.error("     - GND connected between devices if needed")
            logger.error("  2. Verify port permissions:")
            logger.error("     - ls -l /dev/ttyUSB*")
            logger.error("     - sudo usermod -a -G dialout $USER")
            logger.error("  3. Check for other processes using these ports:")
            logger.error("     - lsof | grep ttyUSB")
            logger.error("  4. Verify RS422 adapter is powered on")
            logger.error("  5. Run diagnostic_serial_test.py to verify hardware")
            return_code = 1
        
        # Close ports
        sender.close()
        receiver.close()
        
        return return_code
        
    except serial.SerialException as e:
        logger.error(f"✗ Serial port error: {e}")
        logger.error("")
        logger.error("Possible causes:")
        logger.error("  - Ports don't exist (check: ls /dev/ttyUSB*)")
        logger.error("  - Permission denied (try: sudo chmod 666 /dev/ttyUSB*)")
        logger.error("  - Ports in use by another process")
        return 1
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(test_simple_loopback())
