#!/usr/bin/env python3
"""
Complete Loopback Test for All Devices (ARS, Magnetometer, Reaction Wheel)

Tests all three RS422 loopback pairs:
- ttyUSB0 → ttyUSB1 (ARS)
- ttyUSB2 → ttyUSB3 (Magnetometer)  
- ttyUSB4 → ttyUSB5 (Reaction Wheel)

Uses the simple direct serial approach that works.
"""

import serial
import time
from device_encoders.ars_encoder import ARSEncoder
from device_encoders.magnetometer_encoder import MagnetometerEncoder
from device_encoders.reaction_wheel_encoder import ReactionWheelEncoder

def test_ars_loopback():
    """Test ARS device loopback (ttyUSB0 → ttyUSB1)"""
    print("\n" + "="*60)
    print("Testing ARS Loopback (ttyUSB0 → ttyUSB1)")
    print("="*60)
    
    # Create test data (12 floats for ARS)
    test_data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]
    
    # Encode the packet
    encoder = ARSEncoder()
    packet = encoder.convert_matlab_data(test_data)
    if not packet:
        print("❌ Failed to create ARS packet")
        return False
    
    encoded_data = encoder.encode_packet(packet)
    print(f"Test data: {test_data}")
    print(f"Encoded packet: {encoded_data.hex().upper()}")
    print(f"Packet length: {len(encoded_data)} bytes")
    
    try:
        # Open ports
        send_port = serial.Serial(
            port='/dev/ttyUSB0',
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.0
        )
        
        receive_port = serial.Serial(
            port='/dev/ttyUSB1',
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=3.0
        )
        
        # Clear buffers
        send_port.reset_input_buffer()
        send_port.reset_output_buffer()
        receive_port.reset_input_buffer()
        receive_port.reset_output_buffer()
        
        print("\n📤 Sending data on ttyUSB0...")
        bytes_written = send_port.write(encoded_data)
        send_port.flush()
        print(f"Sent {bytes_written} bytes")
        
        # Wait for data to propagate
        time.sleep(0.5)
        
        print("📥 Reading data from ttyUSB1...")
        received_data = receive_port.read(len(encoded_data))
        
        if received_data:
            print(f"Received {len(received_data)} bytes: {received_data.hex().upper()}")
            
            if received_data == encoded_data:
                print("✅ ARS LOOPBACK TEST PASSED!")
                return True
            else:
                print("❌ Data mismatch!")
                return False
        else:
            print("❌ No data received")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        send_port.close()
        receive_port.close()

def test_magnetometer_loopback():
    """Test Magnetometer device loopback (ttyUSB2 → ttyUSB3)"""
    print("\n" + "="*60)
    print("Testing Magnetometer Loopback (ttyUSB2 → ttyUSB3)")
    print("="*60)
    
    # Create test data (3 floats for Magnetometer: X, Y, Z magnetic field)
    test_data = [25000.0, -5000.0, 40000.0]  # nT
    
    # Encode the packet
    encoder = MagnetometerEncoder()
    encoded_data = encoder.process_matlab_data_rs485(test_data)
    if not encoded_data:
        print("❌ Failed to create Magnetometer packet")
        return False
    
    print(f"Test data: {test_data}")
    print(f"Encoded packet: {encoded_data.hex().upper()}")
    print(f"Packet length: {len(encoded_data)} bytes")
    
    try:
        # Open ports
        send_port = serial.Serial(
            port='/dev/ttyUSB2',
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.0
        )
        
        receive_port = serial.Serial(
            port='/dev/ttyUSB3',
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=3.0
        )
        
        # Clear buffers
        send_port.reset_input_buffer()
        send_port.reset_output_buffer()
        receive_port.reset_input_buffer()
        receive_port.reset_output_buffer()
        
        print("\n📤 Sending data on ttyUSB2...")
        bytes_written = send_port.write(encoded_data)
        send_port.flush()
        print(f"Sent {bytes_written} bytes")
        
        # Wait for data to propagate
        time.sleep(0.5)
        
        print("📥 Reading data from ttyUSB3...")
        received_data = receive_port.read(len(encoded_data))
        
        if received_data:
            print(f"Received {len(received_data)} bytes: {received_data.hex().upper()}")
            
            if received_data == encoded_data:
                print("✅ MAGNETOMETER LOOPBACK TEST PASSED!")
                return True
            else:
                print("❌ Data mismatch!")
                return False
        else:
            print("❌ No data received")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        send_port.close()
        receive_port.close()

def test_reaction_wheel_loopback():
    """Test Reaction Wheel device loopback (ttyUSB4 → ttyUSB5)"""
    print("\n" + "="*60)
    print("Testing Reaction Wheel Loopback (ttyUSB4 → ttyUSB5)")
    print("="*60)
    
    # Create test data (4 floats for Reaction Wheel: speed, current, temp, voltage)
    test_data = [1500.0, 2.5, 35.0, 28.5]
    
    # Encode the packet
    encoder = ReactionWheelEncoder()
    encoded_data = encoder.process_matlab_data_health(test_data)
    if not encoded_data:
        print("❌ Failed to create Reaction Wheel packet")
        return False
    
    print(f"Test data: {test_data}")
    print(f"Encoded packet: {encoded_data.hex().upper()}")
    print(f"Packet length: {len(encoded_data)} bytes")
    
    try:
        # Open ports
        send_port = serial.Serial(
            port='/dev/ttyUSB4',
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.0
        )
        
        receive_port = serial.Serial(
            port='/dev/ttyUSB5',
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=3.0
        )
        
        # Clear buffers
        send_port.reset_input_buffer()
        send_port.reset_output_buffer()
        receive_port.reset_input_buffer()
        receive_port.reset_output_buffer()
        
        print("\n📤 Sending data on ttyUSB4...")
        bytes_written = send_port.write(encoded_data)
        send_port.flush()
        print(f"Sent {bytes_written} bytes")
        
        # Wait for data to propagate
        time.sleep(0.5)
        
        print("📥 Reading data from ttyUSB5...")
        received_data = receive_port.read(len(encoded_data))
        
        if received_data:
            print(f"Received {len(received_data)} bytes: {received_data.hex().upper()}")
            
            if received_data == encoded_data:
                print("✅ REACTION WHEEL LOOPBACK TEST PASSED!")
                return True
            else:
                print("❌ Data mismatch!")
                return False
        else:
            print("❌ No data received")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        send_port.close()
        receive_port.close()

def main():
    """Run all loopback tests"""
    print("\n" + "="*60)
    print("Aurora FlatSat Simulator - Complete Loopback Test")
    print("="*60)
    print("\nTesting RS422 hardware loopback connections:")
    print("  Port 1 (ttyUSB0) → Port 2 (ttyUSB1) [ARS]")
    print("  Port 3 (ttyUSB2) → Port 4 (ttyUSB3) [Magnetometer]")
    print("  Port 5 (ttyUSB4) → Port 6 (ttyUSB5) [Reaction Wheel]")
    
    results = []
    
    # Test ARS
    results.append(("ARS", test_ars_loopback()))
    
    # Test Magnetometer
    results.append(("Magnetometer", test_magnetometer_loopback()))
    
    # Test Reaction Wheel
    results.append(("Reaction Wheel", test_reaction_wheel_loopback()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for device, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{device:20s}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All loopback tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == '__main__':
    exit(main())
