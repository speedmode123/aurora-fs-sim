#!/usr/bin/env python3
"""
Reaction Wheel Device Encoder for MATLAB Simulator

Creates Reaction Wheel encoder based on ICD64020011 specification.
Converts MATLAB data to RWA telemetry format for testing satellite systems.
"""

import struct
import time
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class RWAMode(Enum):
    """RWA operation modes"""
    STANDBY = 0
    OPERATE = 1

class RWAStatus(Enum):
    """RWA status codes"""
    NORMAL = 0x00
    WARNING = 0x01
    ERROR = 0x02
    CRITICAL = 0x03
    FAULT = 0x04

class RWATelemetryType(Enum):
    """RWA telemetry message types"""
    HEALTH_STATUS = 0x15
    SPEED_TELEMETRY = 0x16
    CURRENT_TELEMETRY = 0x17
    TEMPERATURE_TELEMETRY = 0x18

@dataclass
class RWAData:
    """RWA data structure for MATLAB input"""
    wheel_speed: float = 0.0  # RPM
    motor_current: float = 0.0  # A
    temperature: float = 25.0  # °C
    bus_voltage: float = 28.0  # V
    power_consumption: float = 0.0  # W
    timestamp: float = 0.0

@dataclass
class RWAPacket:
    """RWA packet structure"""
    wheel_speed: float = 0.0  # RPM
    motor_current: float = 0.0  # A
    temperature: float = 25.0  # °C
    bus_voltage: float = 28.0  # V
    power_consumption: float = 0.0  # W
    status: RWAStatus = RWAStatus.NORMAL
    mode: RWAMode = RWAMode.OPERATE
    telemetry_type: RWATelemetryType = RWATelemetryType.HEALTH_STATUS
    timestamp: float = 0.0

class RWAMessageEncoder:
    """Encodes RWA data into Honeywell protocol format per ICD64020011"""
    
    def __init__(self, rwa_address: int = 0x01):
        self.rwa_address = rwa_address
        self.sequence_counter = 0
        
    def encode_health_status(self, packet: RWAPacket) -> bytes:
        """
        Encode Health & Status telemetry message (OpCode 0x15)
        
        Format: [ADR][OC][DAT[0-18]][CRC]
        """
        # Message header
        message = bytearray()
        message.append(self.rwa_address)  # ADR
        message.append(packet.telemetry_type.value)  # OC
        
        # Status word (DAT[0])
        status_byte = self._build_status_byte(packet)
        message.append(status_byte)
        
        # Reserved bytes (DAT[1-3])
        message.extend([0x00, 0x00, 0x00])
        
        # MRAM State byte (DAT[4])
        mram_state = 0x01  # Enabled
        message.append(mram_state)
        
        # Health & Status word (DAT[5])
        health_status = self._build_health_status_word(packet)
        message.extend(struct.pack('<H', health_status))
        
        # Reserved byte (DAT[6])
        message.append(0x00)
        
        # Temperature (DAT[7-10]) - 32-bit float, big-endian per ICD
        temp_bytes = struct.pack('>f', packet.temperature)
        message.extend(temp_bytes)
        
        # Bus voltage (DAT[11-14]) - 32-bit float, big-endian
        voltage_bytes = struct.pack('>f', packet.bus_voltage)
        message.extend(voltage_bytes)
        
        # Power consumption (DAT[15-18]) - 32-bit float, big-endian
        power_bytes = struct.pack('>f', packet.power_consumption)
        message.extend(power_bytes)
        
        # Calculate CRC (XOR of all bytes except address)
        crc = self._calculate_crc(message[1:])
        message.append(crc)
        
        return bytes(message)
    
    def encode_speed_telemetry(self, packet: RWAPacket) -> bytes:
        """
        Encode Speed telemetry message (OpCode 0x16)
        
        Format: [ADR][OC][DAT[0-7]][CRC]
        """
        message = bytearray()
        message.append(self.rwa_address)  # ADR
        message.append(packet.telemetry_type.value)  # OC
        
        # Status word (DAT[0])
        status_byte = self._build_status_byte(packet)
        message.append(status_byte)
        
        # Reserved bytes (DAT[1-3])
        message.extend([0x00, 0x00, 0x00])
        
        # Wheel speed (DAT[4-7]) - 32-bit float, big-endian
        speed_bytes = struct.pack('>f', packet.wheel_speed)
        message.extend(speed_bytes)
        
        # Calculate CRC
        crc = self._calculate_crc(message[1:])
        message.append(crc)
        
        return bytes(message)
    
    def encode_current_telemetry(self, packet: RWAPacket) -> bytes:
        """
        Encode Current telemetry message (OpCode 0x17)
        
        Format: [ADR][OC][DAT[0-7]][CRC]
        """
        message = bytearray()
        message.append(self.rwa_address)  # ADR
        message.append(packet.telemetry_type.value)  # OC
        
        # Status word (DAT[0])
        status_byte = self._build_status_byte(packet)
        message.append(status_byte)
        
        # Reserved bytes (DAT[1-3])
        message.extend([0x00, 0x00, 0x00])
        
        # Motor current (DAT[4-7]) - 32-bit float, big-endian
        current_bytes = struct.pack('>f', packet.motor_current)
        message.extend(current_bytes)
        
        # Calculate CRC
        crc = self._calculate_crc(message[1:])
        message.append(crc)
        
        return bytes(message)
    
    def _build_status_byte(self, packet: RWAPacket) -> int:
        """Build status byte per ICD specification"""
        status = 0
        
        # Bit 0: Start bit (always 0)
        # Bit 1: Reserved (always 0)
        # Bit 2-6: Last command OpCode echo back (0 for telemetry)
        # Bit 7: Fault status
        if packet.status == RWAStatus.FAULT:
            status |= 0x80
        
        # Bit 8: Current operation mode
        if packet.mode == RWAMode.STANDBY:
            status |= 0x01
        
        # Bit 9: Parity bit (even)
        # Bit 10: Stop bit (always 1)
        
        return status & 0xFF
    
    def _build_health_status_word(self, packet: RWAPacket) -> int:
        """Build health & status word"""
        status = 0
        
        # Bit 0: Over-current error flag
        if packet.motor_current > 9.76:  # Threshold from ICD
            status |= 0x01
        
        # Bit 1: Bus over voltage flag
        if packet.bus_voltage > 42.0:  # Threshold from ICD
            status |= 0x02
        
        # Bit 2: Bus under voltage flag
        if packet.bus_voltage < 19.0:  # Threshold from ICD
            status |= 0x04
        
        # Bit 5: Angular position error flag
        # Bit 7: Wheel over speed flag
        if packet.wheel_speed > 4200.0:  # Threshold from ICD
            status |= 0x80
        
        return status & 0xFFFF
    
    def _calculate_crc(self, data: bytes) -> int:
        """Calculate CRC as bitwise XOR per ICD specification"""
        crc = 0
        for byte in data:
            crc ^= byte
        return crc & 0xFF

class ReactionWheelEncoder:
    """Converts MATLAB RWA data to Honeywell format"""
    
    def __init__(self, rwa_address: int = 0x01):
        self.message_encoder = RWAMessageEncoder(rwa_address)
        self.message_counter = 0
        
    def convert_matlab_data(self, matlab_data: List[float]) -> Optional[RWAPacket]:
        """
        Convert MATLAB data to RWA packet
        
        Args:
            matlab_data: List of 4 floats from MATLAB [wheel_speed, motor_current, temperature, bus_voltage]
        
        Returns:
            RWAPacket or None if invalid data
        """
        if len(matlab_data) != 4:
            logger.error(f"Expected 4 floats from MATLAB, got {len(matlab_data)}")
            return None
        
        # Create RWA data structure
        rwa_data = RWAData(
            wheel_speed=matlab_data[0],
            motor_current=matlab_data[1],
            temperature=matlab_data[2],
            bus_voltage=matlab_data[3],
            timestamp=time.time()
        )
        
        return self.convert_rwa_data(rwa_data)
    
    def convert_rwa_data(self, rwa_data: RWAData) -> RWAPacket:
        """Convert RWA data to packet format"""
        
        packet = RWAPacket(
            wheel_speed=rwa_data.wheel_speed,
            motor_current=rwa_data.motor_current,
            temperature=rwa_data.temperature,
            bus_voltage=rwa_data.bus_voltage,
            power_consumption=rwa_data.power_consumption,
            timestamp=rwa_data.timestamp
        )
        
        # Calculate power consumption
        packet.power_consumption = abs(packet.motor_current * packet.bus_voltage)
        
        # Determine status and mode based on data quality
        self._update_status_and_mode(packet)
        
        self.message_counter += 1
        return packet
    
    def _update_status_and_mode(self, packet: RWAPacket):
        """Update packet status and mode based on data quality"""
        
        # Check for critical conditions
        if (packet.wheel_speed > 4200.0 or 
            packet.motor_current > 9.76 or 
            packet.bus_voltage > 42.0 or 
            packet.bus_voltage < 19.0):
            packet.status = RWAStatus.CRITICAL
        elif (packet.wheel_speed > 4000.0 or 
              packet.motor_current > 8.0 or 
              packet.bus_voltage > 40.0 or 
              packet.bus_voltage < 20.0):
            packet.status = RWAStatus.WARNING
        else:
            packet.status = RWAStatus.NORMAL
        
        # Determine mode based on wheel speed
        if abs(packet.wheel_speed) < 10.0:  # Threshold for standby
            packet.mode = RWAMode.STANDBY
        else:
            packet.mode = RWAMode.OPERATE
    
    def encode_health_status(self, packet: RWAPacket) -> bytes:
        """Encode packet as Health & Status telemetry"""
        packet.telemetry_type = RWATelemetryType.HEALTH_STATUS
        return self.message_encoder.encode_health_status(packet)
    
    def encode_speed_telemetry(self, packet: RWAPacket) -> bytes:
        """Encode packet as Speed telemetry"""
        packet.telemetry_type = RWATelemetryType.SPEED_TELEMETRY
        return self.message_encoder.encode_speed_telemetry(packet)
    
    def encode_current_telemetry(self, packet: RWAPacket) -> bytes:
        """Encode packet as Current telemetry"""
        packet.telemetry_type = RWATelemetryType.CURRENT_TELEMETRY
        return self.message_encoder.encode_current_telemetry(packet)
    
    def process_matlab_data_health(self, matlab_data: List[float]) -> Optional[bytes]:
        """
        Complete processing pipeline: MATLAB data -> packet -> Health & Status encoded bytes
        
        Args:
            matlab_data: List of 4 floats from MATLAB
            
        Returns:
            Encoded bytes ready for transmission or None if error
        """
        packet = self.convert_matlab_data(matlab_data)
        if packet is None:
            return None
        
        return self.encode_health_status(packet)
    
    def process_matlab_data_speed(self, matlab_data: List[float]) -> Optional[bytes]:
        """
        Complete processing pipeline: MATLAB data -> packet -> Speed telemetry encoded bytes
        
        Args:
            matlab_data: List of 4 floats from MATLAB
            
        Returns:
            Encoded bytes ready for transmission or None if error
        """
        packet = self.convert_matlab_data(matlab_data)
        if packet is None:
            return None
        
        return self.encode_speed_telemetry(packet)
    
    def process_matlab_data_current(self, matlab_data: List[float]) -> Optional[bytes]:
        """
        Complete processing pipeline: MATLAB data -> packet -> Current telemetry encoded bytes
        
        Args:
            matlab_data: List of 4 floats from MATLAB
            
        Returns:
            Encoded bytes ready for transmission or None if error
        """
        packet = self.convert_matlab_data(matlab_data)
        if packet is None:
            return None
        
        return self.encode_current_telemetry(packet)

def main():
    """Test Reaction Wheel encoder"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Reaction Wheel Encoder Test')
    parser.add_argument('--test-data', action='store_true', help='Run with test data')
    parser.add_argument('--telemetry-type', choices=['health', 'speed', 'current'], default='health', help='Telemetry type to test')
    
    args = parser.parse_args()
    
    encoder = ReactionWheelEncoder()
    
    if args.test_data:
        # Test with sample data
        test_data = [1500.0, 2.5, 35.0, 28.5]  # Speed, Current, Temp, Voltage
        
        print(f"Testing Reaction Wheel Encoder with sample data:")
        print(f"Input: {test_data}")
        
        # Process data
        if args.telemetry_type == 'health':
            encoded_bytes = encoder.process_matlab_data_health(test_data)
        elif args.telemetry_type == 'speed':
            encoded_bytes = encoder.process_matlab_data_speed(test_data)
        else:  # current
            encoded_bytes = encoder.process_matlab_data_current(test_data)
        
        if encoded_bytes:
            print(f"Encoded packet: {encoded_bytes.hex().upper()}")
            print(f"Packet length: {len(encoded_bytes)} bytes")
        else:
            print("Failed to encode data")
        
        # Show packet details
        packet = encoder.convert_matlab_data(test_data)
        if packet:
            print(f"\nPacket details:")
            print(f"Wheel speed: {packet.wheel_speed:.1f} RPM")
            print(f"Motor current: {packet.motor_current:.2f} A")
            print(f"Temperature: {packet.temperature:.1f}°C")
            print(f"Bus voltage: {packet.bus_voltage:.1f} V")
            print(f"Power consumption: {packet.power_consumption:.1f} W")
            print(f"Status: {packet.status.name}")
            print(f"Mode: {packet.mode.name}")
    else:
        print("Reaction Wheel Encoder ready for MATLAB data")
        print("Use --test-data to run with sample data")

if __name__ == '__main__':
    main()
