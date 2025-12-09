#!/usr/bin/env python3
"""
Magnetometer Device Encoder for MATLAB Simulator

Adapts the magnetometer encoder from honeywell_magnetometer.py to work with
MATLAB data input. Converts 3 floats from MATLAB to CAN/RS485 format.
"""

import struct
import time
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class MagnetometerStatus(Enum):
    """Magnetometer status codes based on ICD specifications"""
    NORMAL = 0x00
    WARNING = 0x01
    ERROR = 0x02
    CRITICAL = 0x03
    CALIBRATION_MODE = 0x04
    MEMORY_ERROR = 0x05
    COMMUNICATION_ERROR = 0x06

class MessageType(Enum):
    """Message types from ICD specifications"""
    MAGDATA = 0x01
    MAGTEMP = 0x02
    MAGID = 0x03
    MEMREAD = 0x04
    MEMWRITE = 0x05
    MEMCMD = 0x06
    OPMODE = 0x07
    STATUS = 0x08

@dataclass
class MagnetometerData:
    """Magnetometer data structure for MATLAB input"""
    x_field: float = 0.0  # nT
    y_field: float = 0.0  # nT
    z_field: float = 0.0  # nT
    temperature: float = 25.0  # °C
    timestamp: float = 0.0

@dataclass
class MagnetometerPacket:
    """Magnetometer packet structure"""
    x_field: float = 0.0  # nT
    y_field: float = 0.0  # nT
    z_field: float = 0.0  # nT
    temperature: float = 25.0  # °C
    status: MagnetometerStatus = MagnetometerStatus.NORMAL
    message_type: MessageType = MessageType.MAGDATA
    timestamp: float = 0.0

class CANEncoder:
    """Encodes magnetometer data for CAN output per ICD56011974-CAN"""
    
    # CAN Message IDs from ICD56011974-CAN
    CAN_DATA_ID = 0x101
    CAN_TEMP_ID = 0x105
    
    @classmethod
    def encode_magdata(cls, packet: MagnetometerPacket) -> Tuple[int, bytes]:
        """
        Encode magnetometer data for CAN transmission
        
        Returns:
            Tuple of (CAN_ID, data_bytes)
        """
        # Convert magnetic field values to 16-bit signed integers
        # Scale factor from ICD: 1 nT per LSB
        x_field_int = int(packet.x_field) & 0xFFFF
        y_field_int = int(packet.y_field) & 0xFFFF
        z_field_int = int(packet.z_field) & 0xFFFF
        
        # Pack as big-endian per ICD specification
        # Format: [XHI, XLO, YHI, YLO, ZHI, ZLO, STATUS]
        data = bytearray()
        data.extend(struct.pack('>H', x_field_int))  # X field (big-endian)
        data.extend(struct.pack('>H', y_field_int))  # Y field (big-endian)
        data.extend(struct.pack('>H', z_field_int))  # Z field (big-endian)
        data.append(packet.status.value)  # Status byte
        
        return cls.CAN_DATA_ID, bytes(data)
    
    @classmethod
    def encode_magtemp(cls, packet: MagnetometerPacket) -> Tuple[int, bytes]:
        """
        Encode magnetometer temperature for CAN transmission
        
        Returns:
            Tuple of (CAN_ID, data_bytes)
        """
        # Convert temperature to 16-bit signed integer
        # Scale factor: 1°C per LSB
        temp_int = int(packet.temperature) & 0xFFFF
        
        # Pack as big-endian per ICD specification
        # Format: [THI, TLO]
        data = struct.pack('>H', temp_int)
        
        return cls.CAN_TEMP_ID, bytes(data)

class RS485Encoder:
    """Encodes magnetometer data for RS485 output per ICD56011974-RS"""
    
    def __init__(self):
        self.sequence_counter = 0
        
    def encode_magdata(self, packet: MagnetometerPacket) -> bytes:
        """
        Encode magnetometer data for RS485 transmission
        
        Returns:
            Encoded message bytes
        """
        # Message format: [Header][Command][Data][CRC]
        header = struct.pack('<BBH', packet.message_type.value, 0x01, self.sequence_counter)
        
        # Convert magnetic field values to 16-bit signed integers
        x_field_int = int(packet.x_field) & 0xFFFF
        y_field_int = int(packet.y_field) & 0xFFFF
        z_field_int = int(packet.z_field) & 0xFFFF
        
        # Pack data as little-endian per ICD specification
        data = bytearray()
        data.extend(struct.pack('<H', x_field_int))  # X field
        data.extend(struct.pack('<H', y_field_int))  # Y field
        data.extend(struct.pack('<H', z_field_int))  # Z field
        data.append(packet.status.value)  # Status byte
        
        # Calculate CRC-16 over header + command + data
        crc_data = header + bytes([0x01]) + data
        crc = self._calculate_crc16(crc_data)
        
        # Pack CRC as little-endian
        crc_bytes = struct.pack('<H', crc)
        
        self.sequence_counter += 1
        
        return header + bytes([0x01]) + data + crc_bytes
    
    def encode_magtemp(self, packet: MagnetometerPacket) -> bytes:
        """
        Encode magnetometer temperature for RS485 transmission
        
        Returns:
            Encoded message bytes
        """
        # Message format: [Header][Command][Data][CRC]
        header = struct.pack('<BBH', MessageType.MAGTEMP.value, 0x05, self.sequence_counter)
        
        # Convert temperature to 16-bit signed integer
        temp_int = int(packet.temperature) & 0xFFFF
        
        # Pack data as little-endian
        data = struct.pack('<H', temp_int)
        
        # Calculate CRC-16
        crc_data = header + bytes([0x05]) + data
        crc = self._calculate_crc16(crc_data)
        crc_bytes = struct.pack('<H', crc)
        
        self.sequence_counter += 1
        
        return header + bytes([0x05]) + data + crc_bytes
    
    def _calculate_crc16(self, data: bytes) -> int:
        """Calculate CRC-16 checksum"""
        # Simple CRC-16 implementation
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc & 0xFFFF

class MagnetometerEncoder:
    """Converts MATLAB magnetometer data to Honeywell format"""
    
    def __init__(self):
        self.can_encoder = CANEncoder()
        self.rs485_encoder = RS485Encoder()
        self.message_counter = 0
        
    def convert_matlab_data(self, matlab_data: List[float]) -> Optional[MagnetometerPacket]:
        """
        Convert MATLAB data to magnetometer packet
        
        Args:
            matlab_data: List of 3 floats from MATLAB [x_field, y_field, z_field]
        
        Returns:
            MagnetometerPacket or None if invalid data
        """
        if len(matlab_data) != 3:
            logger.error(f"Expected 3 floats from MATLAB, got {len(matlab_data)}")
            return None
        
        # Create magnetometer data structure
        mag_data = MagnetometerData(
            x_field=matlab_data[0],
            y_field=matlab_data[1],
            z_field=matlab_data[2],
            timestamp=time.time()
        )
        
        return self.convert_magnetometer_data(mag_data)
    
    def convert_magnetometer_data(self, mag_data: MagnetometerData) -> MagnetometerPacket:
        """Convert magnetometer data to packet format"""
        
        packet = MagnetometerPacket(
            x_field=mag_data.x_field,
            y_field=mag_data.y_field,
            z_field=mag_data.z_field,
            temperature=mag_data.temperature,
            timestamp=mag_data.timestamp
        )
        
        # Determine status based on data quality
        self._update_status(packet)
        
        self.message_counter += 1
        return packet
    
    def _update_status(self, packet: MagnetometerPacket):
        """Update packet status based on data quality"""
        
        # Check for reasonable magnetic field values
        field_magnitude = (packet.x_field**2 + packet.y_field**2 + packet.z_field**2)**0.5
        
        # Earth's magnetic field is typically 25,000-65,000 nT
        if field_magnitude < 10000 or field_magnitude > 100000:
            packet.status = MagnetometerStatus.ERROR
        elif field_magnitude < 20000 or field_magnitude > 80000:
            packet.status = MagnetometerStatus.WARNING
        else:
            packet.status = MagnetometerStatus.NORMAL
        
        # Check temperature range
        if packet.temperature < -40 or packet.temperature > 85:
            packet.status = MagnetometerStatus.CRITICAL
    
    def encode_can_data(self, packet: MagnetometerPacket) -> Tuple[int, bytes]:
        """Encode packet for CAN transmission"""
        return self.can_encoder.encode_magdata(packet)
    
    def encode_can_temp(self, packet: MagnetometerPacket) -> Tuple[int, bytes]:
        """Encode temperature for CAN transmission"""
        return self.can_encoder.encode_magtemp(packet)
    
    def encode_rs485_data(self, packet: MagnetometerPacket) -> bytes:
        """Encode packet for RS485 transmission"""
        return self.rs485_encoder.encode_magdata(packet)
    
    def encode_rs485_temp(self, packet: MagnetometerPacket) -> bytes:
        """Encode temperature for RS485 transmission"""
        return self.rs485_encoder.encode_magtemp(packet)
    
    def process_matlab_data_can(self, matlab_data: List[float]) -> Optional[Tuple[int, bytes]]:
        """
        Complete processing pipeline: MATLAB data -> packet -> CAN encoded bytes
        
        Args:
            matlab_data: List of 3 floats from MATLAB
            
        Returns:
            Tuple of (CAN_ID, encoded_bytes) or None if error
        """
        packet = self.convert_matlab_data(matlab_data)
        if packet is None:
            return None
        
        return self.encode_can_data(packet)
    
    def process_matlab_data_rs485(self, matlab_data: List[float]) -> Optional[bytes]:
        """
        Complete processing pipeline: MATLAB data -> packet -> RS485 encoded bytes
        
        Args:
            matlab_data: List of 3 floats from MATLAB
            
        Returns:
            Encoded bytes ready for transmission or None if error
        """
        packet = self.convert_matlab_data(matlab_data)
        if packet is None:
            return None
        
        return self.encode_rs485_data(packet)

def main():
    """Test magnetometer encoder"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Magnetometer Encoder Test')
    parser.add_argument('--test-data', action='store_true', help='Run with test data')
    parser.add_argument('--output-format', choices=['can', 'rs485'], default='can', help='Output format to test')
    
    args = parser.parse_args()
    
    encoder = MagnetometerEncoder()
    
    if args.test_data:
        # Test with sample data (typical Earth magnetic field)
        test_data = [25000.0, -5000.0, 40000.0]  # X, Y, Z field in nT
        
        print(f"Testing Magnetometer Encoder with sample data:")
        print(f"Input: {test_data}")
        
        # Process data
        if args.output_format == 'can':
            result = encoder.process_matlab_data_can(test_data)
            if result:
                can_id, encoded_bytes = result
                print(f"CAN ID: 0x{can_id:03X}")
                print(f"Encoded packet: {encoded_bytes.hex().upper()}")
                print(f"Packet length: {len(encoded_bytes)} bytes")
            else:
                print("Failed to encode CAN data")
                
        else:  # rs485
            encoded_bytes = encoder.process_matlab_data_rs485(test_data)
            if encoded_bytes:
                print(f"Encoded packet: {encoded_bytes.hex().upper()}")
                print(f"Packet length: {len(encoded_bytes)} bytes")
            else:
                print("Failed to encode RS485 data")
        
        # Show packet details
        packet = encoder.convert_matlab_data(test_data)
        if packet:
            print(f"\nPacket details:")
            print(f"Magnetic field: X={packet.x_field:.1f}, Y={packet.y_field:.1f}, Z={packet.z_field:.1f} nT")
            print(f"Temperature: {packet.temperature:.1f}°C")
            print(f"Status: {packet.status.name}")
            print(f"Field magnitude: {(packet.x_field**2 + packet.y_field**2 + packet.z_field**2)**0.5:.1f} nT")
    else:
        print("Magnetometer Encoder ready for MATLAB data")
        print("Use --test-data to run with sample data")

if __name__ == '__main__':
    main()
