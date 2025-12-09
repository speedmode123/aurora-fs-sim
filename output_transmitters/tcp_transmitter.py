#!/usr/bin/env python3
"""
TCP Output Transmitter for Device Simulator

Handles TCP/IP communication output for ARS, Magnetometer, and Reaction Wheel devices.
Supports multiple TCP connections with configurable parameters.
"""

import socket
import time
import logging
import threading
from typing import Optional, Dict, Any, Tuple
from queue import Queue, Empty
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TCPConfig:
    """TCP communication configuration"""
    target_ip: str = "192.168.1.200"
    target_port: int = 8000
    timeout: float = 5.0
    keepalive: bool = True
    buffer_size: int = 4096

class TCPTransmitter:
    """Handles TCP communication for device data transmission"""
    
    def __init__(self, config: TCPConfig):
        self.config = config
        self.socket: Optional[socket.socket] = None
        self.is_connected = False
        self.transmit_queue = Queue()
        self.transmit_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.reconnect_thread: Optional[threading.Thread] = None
        
    def connect(self) -> bool:
        """Connect to TCP target"""
        try:
            # Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.config.timeout)
            
            # Configure keepalive
            if self.config.keepalive:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            # Connect to target
            self.socket.connect((self.config.target_ip, self.config.target_port))
            
            self.is_connected = True
            logger.info(f"Connected to TCP target {self.config.target_ip}:{self.config.target_port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to TCP target {self.config.target_ip}:{self.config.target_port}: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from TCP target"""
        self.stop_event.set()
        
        if self.transmit_thread and self.transmit_thread.is_alive():
            self.transmit_thread.join(timeout=2.0)
        
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            self.reconnect_thread.join(timeout=2.0)
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.is_connected = False
            logger.info(f"Disconnected from TCP target {self.config.target_ip}:{self.config.target_port}")
    
    def start_transmission(self):
        """Start transmission thread"""
        if not self.is_connected:
            logger.error("Cannot start transmission: not connected to TCP target")
            return False
        
        self.stop_event.clear()
        self.transmit_thread = threading.Thread(target=self._transmit_loop, daemon=True)
        self.transmit_thread.start()
        logger.info("Started TCP transmission thread")
        return True
    
    def start_reconnection(self):
        """Start reconnection thread"""
        self.reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        self.reconnect_thread.start()
        logger.info("Started TCP reconnection thread")
    
    def send_data(self, data: bytes, device_name: str = "unknown") -> bool:
        """Queue data for transmission"""
        if not self.is_connected:
            logger.warning(f"Cannot send data: not connected to TCP target")
            return False
        
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
                if self.socket and self.is_connected:
                    bytes_sent = self.socket.send(data)
                    logger.debug(f"Sent {bytes_sent} bytes for {device_name}")
                    
                    # Log transmission rate
                    if hasattr(self, '_last_transmit_time'):
                        time_diff = time.time() - self._last_transmit_time
                        if time_diff > 0:
                            rate = bytes_sent / time_diff
                            logger.debug(f"Transmission rate: {rate:.1f} bytes/sec")
                    
                    self._last_transmit_time = time.time()
                else:
                    logger.error("TCP socket not available for transmission")
                
            except Empty:
                # No data in queue, continue
                continue
            except Exception as e:
                logger.error(f"Error in transmission loop: {e}")
                self.is_connected = False
                time.sleep(0.1)
    
    def _reconnect_loop(self):
        """Reconnection loop"""
        while not self.stop_event.is_set():
            if not self.is_connected:
                logger.info("Attempting to reconnect to TCP target...")
                if self.connect():
                    self.start_transmission()
                else:
                    time.sleep(5.0)  # Wait before retry
            else:
                time.sleep(1.0)  # Check connection status
    
    def get_status(self) -> Dict[str, Any]:
        """Get transmitter status"""
        return {
            "connected": self.is_connected,
            "target_ip": self.config.target_ip,
            "target_port": self.config.target_port,
            "queue_size": self.transmit_queue.qsize(),
            "transmitting": self.transmit_thread and self.transmit_thread.is_alive()
        }

class TCPTransmitterManager:
    """Manages multiple TCP transmitters for different devices"""
    
    def __init__(self):
        self.transmitters: Dict[str, TCPTransmitter] = {}
        
    def add_transmitter(self, device_name: str, config: TCPConfig) -> bool:
        """Add a TCP transmitter for a device"""
        if device_name in self.transmitters:
            logger.warning(f"Transmitter for {device_name} already exists")
            return False
        
        transmitter = TCPTransmitter(config)
        if transmitter.connect():
            transmitter.start_transmission()
            transmitter.start_reconnection()
            self.transmitters[device_name] = transmitter
            logger.info(f"Added TCP transmitter for {device_name}")
            return True
        else:
            logger.error(f"Failed to add TCP transmitter for {device_name}")
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
    """Test TCP transmitter"""
    import argparse
    
    parser = argparse.ArgumentParser(description='TCP Transmitter Test')
    parser.add_argument('--target-ip', default='192.168.1.200', help='Target IP address')
    parser.add_argument('--target-port', type=int, default=8000, help='Target port')
    parser.add_argument('--test-data', action='store_true', help='Send test data')
    
    args = parser.parse_args()
    
    # Create configuration
    config = TCPConfig(
        target_ip=args.target_ip,
        target_port=args.target_port
    )
    
    # Create transmitter
    transmitter = TCPTransmitter(config)
    
    if transmitter.connect():
        transmitter.start_transmission()
        transmitter.start_reconnection()
        
        if args.test_data:
            # Send test data
            test_data = b"Hello, TCP World!"
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
        print("Failed to connect to TCP target")

if __name__ == '__main__':
    main()
