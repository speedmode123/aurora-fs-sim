#!/usr/bin/env python3
"""
Serial Output Transmitter for Device Simulator

Handles serial communication output for ARS, Magnetometer, and Reaction Wheel devices.
Supports RS422/RS485 interfaces with configurable parameters.
"""

import serial
import time
import logging
import threading
from typing import Optional, Dict, Any
from queue import Queue, Empty
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SerialConfig:
    """Serial communication configuration"""
    port: str = "/dev/ttyUSB0"
    baud_rate: int = 115200
    data_bits: int = 8
    stop_bits: int = 1
    parity: str = "N"  # N, E, O
    timeout: float = 1.0
    flow_control: str = "none"  # none, xonxoff, rtscts, dsrdtr

class SerialTransmitter:
    """Handles serial communication for device data transmission"""
    
    def __init__(self, config: SerialConfig):
        self.config = config
        self.serial_port: Optional[serial.Serial] = None
        self.is_connected = False
        self.transmit_queue = Queue()
        self.transmit_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
    def connect(self) -> bool:
        """Connect to serial port"""
        try:
            # Check if port exists
            import os
            if not os.path.exists(self.config.port):
                logger.warning(f"Serial port {self.config.port} does not exist - running in simulation mode")
                self.is_connected = False
                return False
            
            self.serial_port = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baud_rate,
                bytesize=self.config.data_bits,
                stopbits=self.config.stop_bits,
                parity=self.config.parity,
                timeout=self.config.timeout
            )
            
            # Configure flow control
            if self.config.flow_control == "xonxoff":
                self.serial_port.xonxoff = True
            elif self.config.flow_control == "rtscts":
                self.serial_port.rtscts = True
            elif self.config.flow_control == "dsrdtr":
                self.serial_port.dsrdtr = True
            
            self.is_connected = True
            logger.info(f"Connected to serial port {self.config.port} at {self.config.baud_rate} baud")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to connect to serial port {self.config.port}: {e} - running in simulation mode")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from serial port"""
        self.stop_event.set()
        
        if self.transmit_thread and self.transmit_thread.is_alive():
            self.transmit_thread.join(timeout=2.0)
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.is_connected = False
            logger.info(f"Disconnected from serial port {self.config.port}")
    
    def start_transmission(self):
        """Start transmission thread"""
        if not self.is_connected:
            logger.error("Cannot start transmission: not connected to serial port")
            return False
        
        self.stop_event.clear()
        self.transmit_thread = threading.Thread(target=self._transmit_loop, daemon=True)
        self.transmit_thread.start()
        logger.info("Started serial transmission thread")
        return True
    
    def send_data(self, data: bytes, device_name: str = "unknown"):
        """Queue data for transmission"""
        if not self.is_connected:
            logger.debug(f"Simulation mode: would send {len(data)} bytes for {device_name}: {data.hex().upper()}")
            return True  # Return True in simulation mode
        
        try:
            self.transmit_queue.put((data, device_name, time.time()), timeout=0.1)
            return True
        except:
            logger.warning(f"Transmit queue full, dropping data from {device_name}")
            return False
    
    def _transmit_loop(self):
        """Main transmission loop"""
        while not self.stop_event.is_set():
            try:
                # Get data from queue with timeout
                data, device_name, timestamp = self.transmit_queue.get(timeout=0.1)
                
                # Send data
                if self.serial_port and self.serial_port.is_open:
                    bytes_written = self.serial_port.write(data)
                    self.serial_port.flush()
                    
                    logger.debug(f"Sent {bytes_written} bytes for {device_name}")
                    
                    # Log transmission rate
                    if hasattr(self, '_last_transmit_time'):
                        time_diff = time.time() - self._last_transmit_time
                        if time_diff > 0:
                            rate = bytes_written / time_diff
                            logger.debug(f"Transmission rate: {rate:.1f} bytes/sec")
                    
                    self._last_transmit_time = time.time()
                else:
                    logger.error("Serial port not available for transmission")
                
            except Empty:
                # No data in queue, continue
                continue
            except Exception as e:
                logger.error(f"Error in transmission loop: {e}")
                time.sleep(0.1)
    
    def get_status(self) -> Dict[str, Any]:
        """Get transmitter status"""
        return {
            "connected": self.is_connected,
            "port": self.config.port,
            "baud_rate": self.config.baud_rate,
            "queue_size": self.transmit_queue.qsize(),
            "transmitting": self.transmit_thread and self.transmit_thread.is_alive()
        }

class SerialTransmitterManager:
    """Manages multiple serial transmitters for different devices"""
    
    def __init__(self):
        self.transmitters: Dict[str, SerialTransmitter] = {}
        
    def add_transmitter(self, device_name: str, config: SerialConfig) -> bool:
        """Add a serial transmitter for a device"""
        if device_name in self.transmitters:
            logger.warning(f"Transmitter for {device_name} already exists")
            return False
        
        transmitter = SerialTransmitter(config)
        if transmitter.connect():
            transmitter.start_transmission()
            self.transmitters[device_name] = transmitter
            logger.info(f"Added serial transmitter for {device_name}")
            return True
        else:
            logger.error(f"Failed to add serial transmitter for {device_name}")
            return False
    
    def send_data(self, device_name: str, data: bytes) -> bool:
        """Send data for a specific device"""
        if device_name not in self.transmitters:
            logger.error(f"No transmitter found for device {device_name}")
            return False
        
        return self.transmitters[device_name].send_data(data, device_name)
    
    def disconnect_all(self):
        """Disconnect all transmitters"""
        for device_name, transmitter in self.transmitters.items():
            transmitter.disconnect()
            logger.info(f"Disconnected transmitter for {device_name}")
        
        self.transmitters.clear()
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all transmitters"""
        status = {}
        for device_name, transmitter in self.transmitters.items():
            status[device_name] = transmitter.get_status()
        return status

def main():
    """Test serial transmitter"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Serial Transmitter Test')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    parser.add_argument('--test-data', action='store_true', help='Send test data')
    
    args = parser.parse_args()
    
    # Create configuration
    config = SerialConfig(
        port=args.port,
        baud_rate=args.baud
    )
    
    # Create transmitter
    transmitter = SerialTransmitter(config)
    
    if transmitter.connect():
        transmitter.start_transmission()
        
        if args.test_data:
            # Send test data
            test_data = b"Hello, Serial World!"
            print(f"Sending test data: {test_data}")
            
            for i in range(10):
                transmitter.send_data(test_data, "test_device")
                time.sleep(0.1)
            
            # Wait for transmission to complete
            time.sleep(2.0)
        
        # Show status
        status = transmitter.get_status()
        print(f"Transmitter status: {status}")
        
        transmitter.disconnect()
    else:
        print("Failed to connect to serial port")

if __name__ == '__main__':
    main()
