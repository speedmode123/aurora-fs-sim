#!/usr/bin/env python3
"""
Simplified USB Loopback Handler - Direct Serial Communication

Uses the working approach from simple_loopback_test.py:
- Direct serial communication without threads
- No queues or complex monitoring
- Simple blocking reads with in_waiting checks
"""

import serial
import time
import logging
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)

@dataclass
class USBPortConfig:
    """Configuration for USB port pair"""
    send_port: str
    receive_port: str
    baud_rate: int = 115200

@dataclass
class LoopbackResult:
    """Result of a loopback test"""
    success: bool
    bytes_sent: int
    bytes_received: int
    latency_ms: float
    error_message: str = ""

class SimpleUSBLoopback:
    """Simple USB loopback handler using direct serial communication"""
    
    def __init__(self, port_configs: Dict[str, USBPortConfig]):
        """
        Initialize with port configurations
        
        Args:
            port_configs: Dictionary of {device_name: USBPortConfig}
        """
        self.port_configs = port_configs
        self.serial_pairs: Dict[str, tuple] = {}  # {device_name: (sender, receiver)}
        
    def open_ports(self) -> bool:
        """Open all serial port pairs"""
        try:
            for device_name, config in self.port_configs.items():
                logger.info(f"Opening loopback ports for {device_name}:")
                logger.info(f"  Send: {config.send_port} @ {config.baud_rate} baud")
                logger.info(f"  Receive: {config.receive_port} @ {config.baud_rate} baud")
                
                # Open sender port
                sender = serial.Serial(
                    port=config.send_port,
                    baudrate=config.baud_rate,
                    bytesize=8,
                    stopbits=1,
                    parity='N',
                    timeout=1.0,
                    write_timeout=1.0
                )
                
                # Open receiver port
                receiver = serial.Serial(
                    port=config.receive_port,
                    baudrate=config.baud_rate,
                    bytesize=8,
                    stopbits=1,
                    parity='N',
                    timeout=2.0
                )
                
                # Clear buffers
                sender.reset_output_buffer()
                receiver.reset_input_buffer()
                
                self.serial_pairs[device_name] = (sender, receiver)
                logger.info(f"  ✓ Opened loopback pair for {device_name}")
            
            return True
            
        except serial.SerialException as e:
            logger.error(f"Failed to open serial ports: {e}")
            self.close_ports()
            return False
        except Exception as e:
            logger.error(f"Unexpected error opening ports: {e}")
            self.close_ports()
            return False
    
    def test_packet(self, device_name: str, packet: bytes) -> LoopbackResult:
        """
        Test a packet through loopback using direct serial communication
        
        Args:
            device_name: Name of the device
            packet: Packet bytes to send
            
        Returns:
            LoopbackResult with test results
        """
        if device_name not in self.serial_pairs:
            return LoopbackResult(
                success=False,
                bytes_sent=0,
                bytes_received=0,
                latency_ms=0.0,
                error_message=f"No serial pair configured for {device_name}"
            )
        
        sender, receiver = self.serial_pairs[device_name]
        
        try:
            # Clear buffers before test
            receiver.reset_input_buffer()
            sender.reset_output_buffer()
            time.sleep(0.05)  # Small delay for buffer clear
            
            # Send packet
            start_time = time.time()
            bytes_written = sender.write(packet)
            sender.flush()
            
            # Wait for data to propagate
            time.sleep(0.1)
            
            # Check what's available
            waiting = receiver.in_waiting
            
            # Read available data
            received = b''
            if waiting > 0:
                received = receiver.read(waiting)
            
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            
            # Verify data match
            success = (received == packet)
            
            if not success and len(received) > 0:
                error_msg = f"Data mismatch: sent {len(packet)} bytes, received {len(received)} bytes"
            elif not success:
                error_msg = f"No data received (expected {len(packet)} bytes)"
            else:
                error_msg = ""
            
            return LoopbackResult(
                success=success,
                bytes_sent=bytes_written,
                bytes_received=len(received),
                latency_ms=latency_ms,
                error_message=error_msg
            )
            
        except Exception as e:
            logger.error(f"Error testing packet for {device_name}: {e}")
            return LoopbackResult(
                success=False,
                bytes_sent=0,
                bytes_received=0,
                latency_ms=0.0,
                error_message=str(e)
            )
    
    def close_ports(self):
        """Close all serial ports"""
        for device_name, (sender, receiver) in self.serial_pairs.items():
            try:
                sender.close()
                receiver.close()
                logger.info(f"Closed loopback ports for {device_name}")
            except Exception as e:
                logger.error(f"Error closing ports for {device_name}: {e}")
        
        self.serial_pairs.clear()
