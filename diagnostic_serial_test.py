#!/usr/bin/env python3
"""
Minimal Serial Loopback Diagnostic Test

Tests serial communication without any complex threading or queue logic.
This helps isolate whether the issue is with serial communication or the monitoring system.
"""

import serial
import time
import sys

def test_simple_serial_loopback():
    """Test serial ports with minimal code"""
    print("=" * 70)
    print("Diagnostic Serial Loopback Test")
    print("=" * 70)
    print()
    print("Testing: /dev/ttyUSB0 (TX) -> /dev/ttyUSB1 (RX)")
    print()
    
    # Test data
    test_data = bytes([0xAA, 0x01, 0x02, 0x03, 0x04, 0x05])
    print(f"Test data: {test_data.hex().upper()} ({len(test_data)} bytes)")
    print()
    
    try:
        # Open both ports
        print("Opening serial ports...")
        sender = serial.Serial(
            port='/dev/ttyUSB0',
            baudrate=115200,
            bytesize=8,
            stopbits=1,
            parity='N',
            timeout=1.0,
            write_timeout=1.0
        )
        print(f"  ✓ Opened {sender.port} for sending")
        
        receiver = serial.Serial(
            port='/dev/ttyUSB1',
            baudrate=115200,
            bytesize=8,
            stopbits=1,
            parity='N',
            timeout=2.0
        )
        print(f"  ✓ Opened {receiver.port} for receiving")
        print()
        
        # Clear any existing data
        receiver.reset_input_buffer()
        sender.reset_output_buffer()
        time.sleep(0.1)
        
        # Send data
        print(f"Sending {len(test_data)} bytes...")
        bytes_written = sender.write(test_data)
        sender.flush()
        print(f"  ✓ Wrote {bytes_written} bytes to {sender.port}")
        print()
        
        # Small delay for data to propagate
        time.sleep(0.5)
        
        # Check what's available
        waiting = receiver.in_waiting
        print(f"Bytes waiting in receive buffer: {waiting}")
        print()
        
        # Read data
        print("Reading data...")
        received = receiver.read(len(test_data))
        print(f"  ✓ Read {len(received)} bytes from {receiver.port}")
        
        if received:
            print(f"  Received: {received.hex().upper()}")
            print()
            
            # Compare
            if received == test_data:
                print("=" * 70)
                print("✓ SUCCESS - Data matches!")
                print("=" * 70)
                print()
                print("Your RS422 loopback is working correctly.")
                print("The issue is likely in the monitoring thread logic.")
                return_code = 0
            else:
                print("=" * 70)
                print("✗ FAIL - Data mismatch")
                print("=" * 70)
                print(f"Expected: {test_data.hex().upper()}")
                print(f"Received: {received.hex().upper()}")
                return_code = 1
        else:
            print()
            print("=" * 70)
            print("✗ FAIL - No data received")
            print("=" * 70)
            print()
            print("Troubleshooting:")
            print("  1. Check physical wiring:")
            print("     - TX pin of ttyUSB0 connected to RX pin of ttyUSB1")
            print("     - GND connected between devices if needed")
            print("  2. Verify port permissions:")
            print("     - ls -l /dev/ttyUSB*")
            print("     - Add user to dialout group if needed")
            print("  3. Check for other processes using these ports:")
            print("     - lsof | grep ttyUSB")
            print("  4. Verify RS422 adapter is powered on")
            return_code = 1
        
        # Close ports
        sender.close()
        receiver.close()
        
        return return_code
        
    except serial.SerialException as e:
        print(f"\n✗ Serial port error: {e}")
        print("\nPossible causes:")
        print("  - Ports don't exist (check: ls /dev/ttyUSB*)")
        print("  - Permission denied (try: sudo chmod 666 /dev/ttyUSB*)")
        print("  - Ports in use by another process")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(test_simple_serial_loopback())
