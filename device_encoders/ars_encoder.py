# Test with Git push
#!/usr/bin/env python3
"""
ARS Device Encoder for MATLAB Simulator

Adapts the rate sensor encoder from rate_sensor_test_generator.py to work with
MATLAB data input. Converts 6 or 12 floats from MATLAB to Honeywell HG4934 format.
Supports data duplication from primary to redundant channels with optional variation.
"""

import struct
import time
import random
import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ARSData:
    """ARS data structure for MATLAB input"""
    # Prime angular rates (ports 0-2)
    prime_x: float = 0.0
    prime_y: float = 0.0
    prime_z: float = 0.0
    
    # Redundant angular rates (ports 3-5)
    redundant_x: float = 0.0
    redundant_y: float = 0.0
    redundant_z: float = 0.0
    
    # Prime summed incremental angles (ports 6-8)
    prime_angle_x: float = 0.0
    prime_angle_y: float = 0.0
    prime_angle_z: float = 0.0
    
    # Redundant summed incremental angles (ports 9-11)
    redundant_angle_x: float = 0.0
    redundant_angle_y: float = 0.0
    redundant_angle_z: float = 0.0
    
    # Metadata
    timestamp: float = 0.0
    message_counter: int = 0

@dataclass
class RateSensorPacket:
    """Rate sensor packet structure matching Honeywell format"""
    # Angular rates (Body, Control Channel) - 2 bytes each, LSB weighting: 600 x 2^-23 rad/sec/LSB
    angular_rate_x: float = 0.0  # rad/sec
    angular_rate_y: float = 0.0  # rad/sec  
    angular_rate_z: float = 0.0  # rad/sec
    
    # Status Word 1 - 2 bytes (see Table 7)
    status_word_1: int = 0x0000
    
    # Status Word 2 - 2 bytes (see Table 8) 
    status_word_2: int = 0x0000
    
    # Status Word 3 - 2 bytes (see Table 9)
    status_word_3: int = 0x0000
    
    # Summed Incremental Angles (Body, Inertial Channel) - 4 bytes each, LSB weighting: 2^-27 rad/LSB
    summed_angle_x: float = 0.0  # rad
    summed_angle_y: float = 0.0  # rad
    summed_angle_z: float = 0.0  # rad
    
    # Additional metadata
    timestamp: float = 0.0
    message_counter: int = 0

class StatusWordBuilder:
    """Helper class for building status words according to Honeywell specification"""
    
    @staticmethod
    def build_status_word_1(
        counter: int = 0,
        bit_mode: int = 1,  # 0=Power-up BIT, 1=Continuous BIT, 2=Initiated BIT
        rate_sensor_failed: bool = False,
        gyro_failed: bool = False,
        agc_voltage_failed: bool = False,
        # Copy Paste from Word 3 bc i think it was in the wrong section
        gyro_a_start_run: bool = True,  # 0=Start, 1=Run
        gyro_b_start_run: bool = True,
        gyro_c_start_run: bool = True,
        gyro_a_fdc: bool = False,  # 0=OK, 1=Failed
        gyro_b_fdc: bool = False,
        gyro_c_fdc: bool = False,
        fdc_failed: bool = False,
        rs_ok: bool = True  # 0=OK, 1=Failed
    ) -> int:
        """Build Status Word 1 according to Table 7"""
        word = 0
        
        # Bit 0-1: 2 Bit Counter (00 01 10 11...)
        word |= (counter & 0x03)
        
        # Bit 2-3: 2 bit BIT-mode indicator
        word |= ((bit_mode & 0x03) << 2)
        
        # Bit 4: Rate Sensor Failed (Latched)
        if rate_sensor_failed:
            word |= (1 << 4)
            
        # Bit 5: Gyro Failed (Latched)  
        if gyro_failed:
            word |= (1 << 5)
            
        # Bit 6: Reserved (always 0)
        
        # Bit 7: AGC Voltage
        if agc_voltage_failed:
            word |= (1 << 7)
            
        # Bit 8: Gyro A Start/Run
        if gyro_a_start_run:
            word |= (1 << 8)
            
        # Bit 9: Gyro B Start/Run
        if gyro_b_start_run:
            word |= (1 << 9)
            
        # Bit 10: Gyro C Start/Run
        if gyro_c_start_run:
            word |= (1 << 10)
            
        # Bit 11: Gyro A FDC
        if gyro_a_fdc:
            word |= (1 << 11)
            
        # Bit 12: Gyro B FDC
        if gyro_b_fdc:
            word |= (1 << 12)
            
        # Bit 13: Gyro C FDC
        if gyro_c_fdc:
            word |= (1 << 13)
            
        # Bit 14: FDC Failed
        if fdc_failed:
            word |= (1 << 14)
            
        # Bit 15: RS OK
        if rs_ok:
            word |= (1 << 15)
            
        return word & 0xFFFF
        # I think Bit 8-15 are missing? Not sure if needed... -AS
        # I added the missing bits -AS
    
    @staticmethod
    def build_status_word_2(
        gyro_temperature_a: int = 25,  # Temperature in °C (LSB=1°C)
        motor_bias_voltage_failed: bool = False,
        start_data_flag: bool = False,  # 0=sensor data, 1=5555h sync data
        processor_failed: bool = False,
        memory_failed: bool = False,
        #Adding Bit 12 - 15
        asic_failed: bool = False,
        gyro_health_failed: bool = False,
        atp_indicator: bool = False # 0=Mode 1, 1=Mode 2
    ) -> int:
        """Build Status Word 2 according to Table 8"""
        word = 0
        
        # Bit 0-7: Gyro Temperature A (LSB=1°C)
        word |= (gyro_temperature_a & 0xFF)
        
        # Bit 8: Motor Bias Voltage
        if motor_bias_voltage_failed:
            word |= (1 << 8)
            
        # Bit 9: Start data flag
        if start_data_flag:
            word |= (1 << 9)
            
        # Bit 10: Processor
        if processor_failed:
            word |= (1 << 10)
            
        # Bit 11: Memory
        if memory_failed:
            word |= (1 << 11)

        # Bit 12: ASIC
        if asic_failed:
            word |= (1 << 12)

        # Bit 13: Gyro Health
        if gyro_health_failed:
            word |= (1 << 13)

        # Bit 14: ATP Indicator
        if atp_indicator:
            word |= (1 << 14)

        # Bit 15: Reserved, Reserved bits are always 0
            
        return word & 0xFFFF
        # Bit 12-15 not mentioned here ? -AS, fixed ? _AS
    
    @staticmethod
    def build_status_word_3(
        gyro_temperature_b: int = 25,  # Temperature in °C (LSB=1°C)
        gyro_temperature_c: int = 25,  # Temperature in °C (LSB=1°C)
        # gyro_a_start_run: bool = True,  # 0=Start, 1=Run
        # gyro_b_start_run: bool = True,
        # gyro_c_start_run: bool = True,
        # gyro_a_fdc: bool = False,  # 0=OK, 1=Failed
        # gyro_b_fdc: bool = False,
        # gyro_c_fdc: bool = False,
        # fdc_failed: bool = False,
        # rs_ok: bool = True  # 0=OK, 1=Failed
    ) -> int:
        """Build Status Word 3 according to Table 9"""
        word = 0
        
       
        # # Bit 8: Gyro A Start/Run
        # if gyro_a_start_run:
        #     word |= (1 << 8)
            
        # # Bit 9: Gyro B Start/Run
        # if gyro_b_start_run:
        #     word |= (1 << 9)
            
        # # Bit 10: Gyro C Start/Run
        # if gyro_c_start_run:
        #     word |= (1 << 10)
            
        # # Bit 11: Gyro A FDC
        # if gyro_a_fdc:
        #     word |= (1 << 11)
            
        # # Bit 12: Gyro B FDC
        # if gyro_b_fdc:
        #     word |= (1 << 12)
            
        # # Bit 13: Gyro C FDC
        # if gyro_c_fdc:
        #     word |= (1 << 13)
            
        # # Bit 14: FDC Failed
        # if fdc_failed:
        #     word |= (1 << 14)
            
        # # Bit 15: RS OK
        # if rs_ok:
        #     word |= (1 << 15)

        #Adding what was actually in table 9 -AS
        # Bit 0-7: Gyro Temperature B (LSB=1°C)
        word |= (gyro_temperature_b & 0xFF)

        # Bit 8-15: Gyro Temperature C (LSB=1°C)
        word |= (gyro_temperature_c & 0xFF)
            
        return word & 0xFFFF
        # not sure if gyro temp b and c are supposed to be here AS

class MessageEncoder:
    """Encodes rate sensor data into Honeywell protocol format"""
     
    # Scale factors from specification # from table 6 AS
    ANGULAR_RATE_SCALE = 600 * (2 ** -23)  # rad/sec/LSB
    ANGLE_SCALE = 2 ** -27  # rad/LSB
    
    @classmethod
    def encode_angular_rate(cls, rate_rad_per_sec: float) -> bytes:
        """Convert angular rate from rad/sec to 16-bit signed integer with overflow protection"""
        try:
            # Validate input
            if not isinstance(rate_rad_per_sec, (int, float)):
                raise ValueError(f"Invalid input type: {type(rate_rad_per_sec)}")
            
            # Check for extreme values that could cause overflow
            if abs(rate_rad_per_sec) > 1e6:  # Very large values
                logger.warning(f"Extreme angular rate value: {rate_rad_per_sec}")
                rate_rad_per_sec = max(-1e6, min(1e6, rate_rad_per_sec))
            
            # Convert to LSB units with overflow protection
            try:
                lsb_value = int(rate_rad_per_sec / cls.ANGULAR_RATE_SCALE)
            except OverflowError:
                logger.error(f"Overflow in angular rate conversion: {rate_rad_per_sec}")
                # Clamp to maximum representable value
                lsb_value = 32767 if rate_rad_per_sec > 0 else -32768
            
            # Clamp to 16-bit signed range
            lsb_value = max(-32768, min(32767, lsb_value))
            
            # Pack as little-endian 16-bit signed integer
            return struct.pack('<h', lsb_value)
            
        except Exception as e:
            logger.error(f"Error encoding angular rate {rate_rad_per_sec}: {e}")
            # Return zero value as fallback
            return struct.pack('<h', 0)
    
    @classmethod
    def encode_angle(cls, angle_rad: float) -> bytes:
        """Convert angle from rad to 32-bit signed integer with overflow protection"""
        try:
            # Validate input
            if not isinstance(angle_rad, (int, float)):
                raise ValueError(f"Invalid input type: {type(angle_rad)}")
            
            # Check for extreme values that could cause overflow
            if abs(angle_rad) > 1e6:  # Very large values
                logger.warning(f"Extreme angle value: {angle_rad}")
                angle_rad = max(-1e6, min(1e6, angle_rad))
            
            # Convert to LSB units with overflow protection
            try:
                lsb_value = int(angle_rad / cls.ANGLE_SCALE)
            except OverflowError:
                logger.error(f"Overflow in angle conversion: {angle_rad}")
                # Clamp to maximum representable value
                lsb_value = 2147483647 if angle_rad > 0 else -2147483648
            
            # Clamp to 32-bit signed range
            lsb_value = max(-2147483648, min(2147483647, lsb_value))
            
            # Pack as little-endian 32-bit signed integer
            return struct.pack('<i', lsb_value)
            
        except Exception as e:
            logger.error(f"Error encoding angle {angle_rad}: {e}")
            # Return zero value as fallback
            return struct.pack('<i', 0)
    
    @classmethod
    def encode_message(cls, data: RateSensorPacket) -> bytes:
        """Encode complete message according to Honeywell protocol"""
        message = bytearray()
        
        # Add sync byte (Rate Sensor address)
        message.append(0xAA)  # Sync byte
        
        # Angular rates (2 bytes each, little-endian)
        message.extend(cls.encode_angular_rate(data.angular_rate_x))
        message.extend(cls.encode_angular_rate(data.angular_rate_y))
        message.extend(cls.encode_angular_rate(data.angular_rate_z))
        
        # Status words (2 bytes each, little-endian)
        message.extend(struct.pack('<H', data.status_word_1))
        message.extend(struct.pack('<H', data.status_word_2))
        message.extend(struct.pack('<H', data.status_word_3))
        
        # Summed incremental angles (4 bytes each, little-endian)
        message.extend(cls.encode_angle(data.summed_angle_x))
        message.extend(cls.encode_angle(data.summed_angle_y))
        message.extend(cls.encode_angle(data.summed_angle_z))
        
        # Calculate and append checksum (16-bit unsigned sum)
        checksum = sum(message[1:]) & 0xFFFF  # Skip sync byte
        message.extend(struct.pack('<H', checksum))
        
        return bytes(message)

class ARSEncoder:
    """Converts MATLAB ARS data to Honeywell rate sensor format"""
    
    def __init__(self, duplicate_to_redundant: bool = False, variation_percent: float = 0.1):
        """
        Initialize ARS encoder
        
        Args:
            duplicate_to_redundant: If True, duplicate primary data to redundant channels
            variation_percent: Random variation to add to redundant data (default 0.1%)
        """
        self.message_counter = 0
        self.status_word_builder = StatusWordBuilder()
        self.last_data_time = 0
        self.duplicate_to_redundant = duplicate_to_redundant
        self.variation_percent = variation_percent
        
    def _add_variation(self, value: float) -> float:
        """Add random variation to a value with overflow protection"""
        try:
            if self.variation_percent == 0.0:
                return value
            
            # Validate input
            if not isinstance(value, (int, float)):
                logger.warning(f"Invalid value type for variation: {type(value)}")
                return value
            
            # Check for extreme values
            if abs(value) > 1e6:
                logger.warning(f"Extreme value for variation: {value}")
                return value
            
            variation = self.variation_percent / 100.0
            factor = 1.0 + random.uniform(-variation, variation)
            
            # Check for overflow in multiplication
            try:
                result = value * factor
                if not (float('-inf') < result < float('inf')):
                    logger.warning(f"Variation resulted in invalid float: {result}")
                    return value
                return result
            except OverflowError:
                logger.warning(f"Overflow in variation calculation: {value} * {factor}")
                return value
                
        except Exception as e:
            logger.error(f"Error adding variation to {value}: {e}")
            return value
        
    def convert_matlab_data(self, matlab_data: List[float]) -> Optional[RateSensorPacket]:
        """
        Convert MATLAB data to rate sensor packet
        
        Args:
            matlab_data: List of 6 or 12 floats from MATLAB
                6 floats (primary only): [prime_x, prime_y, prime_z, 
                                         prime_angle_x, prime_angle_y, prime_angle_z]
                12 floats (primary + redundant): [prime_x, prime_y, prime_z, 
                                                  redundant_x, redundant_y, redundant_z,
                                                  prime_angle_x, prime_angle_y, prime_angle_z, 
                                                  redundant_angle_x, redundant_angle_y, redundant_angle_z]
        
        Returns:
            RateSensorPacket or None if invalid data
        """
        if len(matlab_data) == 6:
            # Primary data only - duplicate to redundant if enabled
            if self.duplicate_to_redundant:
                logger.debug("Duplicating primary data to redundant channels with variation")
                ars_data = ARSData(
                    prime_x=matlab_data[0],
                    prime_y=matlab_data[1],
                    prime_z=matlab_data[2],
                    redundant_x=self._add_variation(matlab_data[0]),
                    redundant_y=self._add_variation(matlab_data[1]),
                    redundant_z=self._add_variation(matlab_data[2]),
                    prime_angle_x=matlab_data[3],
                    prime_angle_y=matlab_data[4],
                    prime_angle_z=matlab_data[5],
                    redundant_angle_x=self._add_variation(matlab_data[3]),
                    redundant_angle_y=self._add_variation(matlab_data[4]),
                    redundant_angle_z=self._add_variation(matlab_data[5]),
                    timestamp=time.time()
                )
            else:
                logger.error("Received 6 floats but duplicate_to_redundant is False. Enable duplication or provide 12 floats.")
                return None
                
        elif len(matlab_data) == 12:
            # Full data with redundant channels
            logger.debug("Using provided primary and redundant data")
            ars_data = ARSData(
                prime_x=matlab_data[0],
                prime_y=matlab_data[1],
                prime_z=matlab_data[2],
                redundant_x=matlab_data[3],
                redundant_y=matlab_data[4],
                redundant_z=matlab_data[5],
                prime_angle_x=matlab_data[6],
                prime_angle_y=matlab_data[7],
                prime_angle_z=matlab_data[8],
                redundant_angle_x=matlab_data[9],
                redundant_angle_y=matlab_data[10],
                redundant_angle_z=matlab_data[11],
                timestamp=time.time()
            )
        else:
            logger.error(f"Expected 6 or 12 floats from MATLAB, got {len(matlab_data)}")
            return None
        
        return self.convert_ars_data(ars_data)
    
    def convert_ars_data(self, ars_data: ARSData) -> RateSensorPacket:
        """Convert ARS data to rate sensor packet format"""
        
        # Use Prime data as primary source (could implement voting logic)
        packet = RateSensorPacket(
            angular_rate_x=ars_data.prime_x,
            angular_rate_y=ars_data.prime_y,
            angular_rate_z=ars_data.prime_z,
            summed_angle_x=ars_data.prime_angle_x,
            summed_angle_y=ars_data.prime_angle_y,
            summed_angle_z=ars_data.prime_angle_z,
            timestamp=ars_data.timestamp,
            message_counter=self.message_counter
        )
        
        # Build status words based on data quality
        self._update_status_words(packet, ars_data)
        
        self.message_counter += 1
        return packet
    
    def _update_status_words(self, packet: RateSensorPacket, ars_data: ARSData):
        """Update status words based on ARS data quality"""
        
        # Check for data availability
        has_data = any([
            ars_data.prime_x != 0 or ars_data.prime_y != 0 or ars_data.prime_z != 0,
            ars_data.redundant_x != 0 or ars_data.redundant_y != 0 or ars_data.redundant_z != 0
        ])
        
        # Check for large discrepancies between prime and redundant
        rate_diff_x = abs(ars_data.prime_x - ars_data.redundant_x)
        rate_diff_y = abs(ars_data.prime_y - ars_data.redundant_y)
        rate_diff_z = abs(ars_data.prime_z - ars_data.redundant_z)
        
        max_rate_diff = max(rate_diff_x, rate_diff_y, rate_diff_z)
        has_discrepancy = max_rate_diff > 0.1  # Threshold for discrepancy
        
        # Check timing
        current_time = time.time()
        time_since_last = current_time - self.last_data_time
        self.last_data_time = current_time
        
        # Build status words
        packet.status_word_1 = self.status_word_builder.build_status_word_1(
            counter=self.message_counter % 4,
            bit_mode=1,  # Continuous BIT
            rate_sensor_failed=not has_data,
            gyro_failed=has_discrepancy,
            agc_voltage_failed=False
            #moving this from status_word_3
            gyro_a_start_run=has_data,
            gyro_b_start_run=has_data,
            gyro_c_start_run=has_data,
            gyro_a_fdc=has_discrepancy,
            gyro_b_fdc=has_discrepancy,
            gyro_c_fdc=has_discrepancy,
            fdc_failed=has_discrepancy,
            rs_ok=has_data and not has_discrepancy
        )
        
        packet.status_word_2 = self.status_word_builder.build_status_word_2(
            gyro_temperature_a=25,  # Simulated temperature
            motor_bias_voltage_failed=False,
            start_data_flag=False,
            processor_failed=False,
            memory_failed=False
            #Added in missing bits _AS
            asic_failed=False
            gyro_health_failed=False
            atp_indicator=False
        )
        
        packet.status_word_3 = self.status_word_builder.build_status_word_3(
            gyro_temperature_b=25,  # Simulated temperature
            gyro_temperature_c=25,  # Simulated temperature
            # gyro_a_start_run=has_data,
            # gyro_b_start_run=has_data,
            # gyro_c_start_run=has_data,
            # gyro_a_fdc=has_discrepancy,
            # gyro_b_fdc=has_discrepancy,
            # gyro_c_fdc=has_discrepancy,
            # fdc_failed=has_discrepancy,
            # rs_ok=has_data and not has_discrepancy
        )
    
    def encode_packet(self, packet: RateSensorPacket) -> bytes:
        """Encode packet to Honeywell format bytes"""
        return MessageEncoder.encode_message(packet)
    
    def process_matlab_data(self, matlab_data: List[float]) -> Optional[bytes]:
        """
        Complete processing pipeline: MATLAB data -> packet -> encoded bytes
        
        Args:
            matlab_data: List of 12 floats from MATLAB
            
        Returns:
            Encoded bytes ready for transmission or None if error
        """
        packet = self.convert_matlab_data(matlab_data)
        if packet is None:
            return None
        
        return self.encode_packet(packet)

def main():
    """Test ARS encoder"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ARS Encoder Test')
    parser.add_argument('--test-data', action='store_true', help='Run with test data')
    
    args = parser.parse_args()
    
    encoder = ARSEncoder()
    
    if args.test_data:
        # Test with sample data
        test_data = [
            0.1, -0.05, 0.02,  # Prime rates
            0.09, -0.051, 0.021,  # Redundant rates
            1.0, -0.5, 0.2,  # Prime angles
            0.99, -0.49, 0.19  # Redundant angles
        ]
        
        print("Testing ARS Encoder with sample data:")
        print(f"Input: {test_data}")
        
        # Process data
        encoded_bytes = encoder.process_matlab_data(test_data)
        
        if encoded_bytes:
            print(f"Encoded packet: {encoded_bytes.hex().upper()}")
            print(f"Packet length: {len(encoded_bytes)} bytes")
            
            # Decode to verify
            packet = encoder.convert_matlab_data(test_data)
            if packet:
                print(f"\nPacket details:")
                print(f"Angular rates: X={packet.angular_rate_x:.6f}, Y={packet.angular_rate_y:.6f}, Z={packet.angular_rate_z:.6f}")
                print(f"Summed angles: X={packet.summed_angle_x:.6f}, Y={packet.summed_angle_y:.6f}, Z={packet.summed_angle_z:.6f}")
                print(f"Status words: SW1=0x{packet.status_word_1:04X}, SW2=0x{packet.status_word_2:04X}, SW3=0x{packet.status_word_3:04X}")
        else:
            print("Failed to encode data")
    else:
        print("ARS Encoder ready for MATLAB data")
        print("Use --test-data to run with sample data")

if __name__ == '__main__':
    main()
