#!/usr/bin/env python3
"""
CAN Output Transmitter for Device Simulator

Handles CAN bus communication output for ARS, Magnetometer, and Reaction Wheel devices.
Supports multiple CAN interfaces with configurable parameters.
"""

import can
import time
import logging
import threading
from typing import Optional, Dict, Any, Tuple
from queue import Queue, Empty
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CANConfig:
    """CAN communication configuration"""
    interface: str = "can0"
    channel: str = "can0"
    bitrate: int = 500000
    can_filters: Optional[list] = None
    timeout: float = 1.0

class CANTransmitter:
    """Handles CAN communication for device data transmission"""
    
    def __init__(self, config: CANConfig):
        self.config = config
        self.can_bus: Optional[can.Bus] = None
        self.is_connected = False
        self.transmit_queue = Queue()
        self.transmit_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
    def connect(self) -> bool:
        """Connect to CAN bus"""
        try:
            # Check if CAN interface exists
            import os
            can_interface_path = f"/sys/class/net/{self.config.channel}"
            if not os.path.exists(can_interface_path):
                logger.warning(f"CAN interface {self.config.channel} does not exist - running in simulation mode")
                self.is_connected = False
                return False
            
            # Create CAN bus
            self.can_bus = can.Bus(
                interface=self.config.interface,
                channel=self.config.channel,
                bitrate=self.config.bitrate,
                can_filters=self.config.can_filters,
                timeout=self.config.timeout
            )
            
            self.is_connected = True
            logger.info(f"Connected to CAN bus {self.config.channel} at {self.config.bitrate} bps")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to connect to CAN bus {self.config.channel}: {e} - running in simulation mode")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from CAN bus"""
        self.stop_event.set()
        
        if self.transmit_thread and self.transmit_thread.is_alive():
            self.transmit_thread.join(timeout=2.0)
        
        if self.can_bus:
            self.can_bus.shutdown()
            self.is_connected = False
            logger.info(f"Disconnected from CAN bus {self.config.channel}")
    
    def start_transmission(self):
        """Start transmission thread"""
        if not self.is_connected:
            logger.error("Cannot start transmission: not connected to CAN bus")
            return False
        
        self.stop_event.clear()
        self.transmit_thread = threading.Thread(target=self._transmit_loop, daemon=True)
        self.transmit_thread.start()
        logger.info("Started CAN transmission thread")
        return True
    
    def send_message(self, can_id: int, data: bytes, device_name: str = "unknown") -> bool:
        """Queue CAN message for transmission"""
        if not self.is_connected:
            logger.debug(f"Simulation mode: would send CAN message ID 0x{can_id:03X} for {device_name}: {data.hex().upper()}")
            return True  # Return True in simulation mode
        
        try:
            message = can.Message(
                arbitration_id=can_id,
                data=data,
                is_extended_id=False
            )
            
            self.transmit_queue.put((message, device_name, time.time()), timeout=0.1)
            return True
        except:
            logger.warning(f"Transmit queue full, dropping message from {device_name}")
            return False
    
    def _transmit_loop(self):
        """Main transmission loop"""
        while not self.stop_event.is_set():
            try:
                # Get message from queue with timeout
                message, device_name, timestamp = self.transmit_queue.get(timeout=0.1)
                
                # Send message
                if self.can_bus:
                    self.can_bus.send(message)
                    logger.debug(f"Sent CAN message ID 0x{message.arbitration_id:03X} for {device_name}")
                    
                    # Log transmission rate
                    if hasattr(self, '_last_transmit_time'):
                        time_diff = time.time() - self._last_transmit_time
                        if time_diff > 0:
                            rate = len(message.data) / time_diff
                            logger.debug(f"Transmission rate: {rate:.1f} bytes/sec")
                    
                    self._last_transmit_time = time.time()
                else:
                    logger.error("CAN bus not available for transmission")
                
            except Empty:
                # No message in queue, continue
                continue
            except Exception as e:
                logger.error(f"Error in transmission loop: {e}")
                time.sleep(0.1)
    
    def get_status(self) -> Dict[str, Any]:
        """Get transmitter status"""
        return {
            "connected": self.is_connected,
            "interface": self.config.interface,
            "channel": self.config.channel,
            "bitrate": self.config.bitrate,
            "queue_size": self.transmit_queue.qsize(),
            "transmitting": self.transmit_thread and self.transmit_thread.is_alive()
        }

class CANTransmitterManager:
    """Manages multiple CAN transmitters for different devices"""
    
    def __init__(self):
        self.transmitters: Dict[str, CANTransmitter] = {}
        
    def add_transmitter(self, device_name: str, config: CANConfig) -> bool:
        """Add a CAN transmitter for a device"""
        if device_name in self.transmitters:
            logger.warning(f"Transmitter for {device_name} already exists")
            return False
        
        transmitter = CANTransmitter(config)
        if transmitter.connect():
            transmitter.start_transmission()
            self.transmitters[device_name] = transmitter
            logger.info(f"Added CAN transmitter for {device_name}")
            return True
        else:
            logger.error(f"Failed to add CAN transmitter for {device_name}")
            return False
    
    def send_message(self, device_name: str, can_id: int, data: bytes) -> bool:
        """Send CAN message for a specific device"""
        if device_name not in self.transmitters:
            logger.error(f"No transmitter found for device {device_name}")
            return False
        
        return self.transmitters[device_name].send_message(can_id, data, device_name)
    
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
    """Test CAN transmitter"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CAN Transmitter Test')
    parser.add_argument('--interface', default='socketcan', help='CAN interface type')
    parser.add_argument('--channel', default='can0', help='CAN channel')
    parser.add_argument('--bitrate', type=int, default=500000, help='CAN bitrate')
    parser.add_argument('--test-data', action='store_true', help='Send test data')
    
    args = parser.parse_args()
    
    # Create configuration
    config = CANConfig(
        interface=args.interface,
        channel=args.channel,
        bitrate=args.bitrate
    )
    
    # Create transmitter
    transmitter = CANTransmitter(config)
    
    if transmitter.connect():
        transmitter.start_transmission()
        
        if args.test_data:
            # Send test data
            test_data = b"Hello, CAN World!"
            test_id = 0x123
            print(f"Sending test CAN message ID 0x{test_id:03X}: {test_data}")
            
            for i in range(10):
                transmitter.send_message(test_id, test_data, "test_device")
                time.sleep(0.1)
            
            # Wait for transmission to complete
            time.sleep(2.0)
        
        # Show status
        status = transmitter.get_status()
        print(f"Transmitter status: {status}")
        
        transmitter.disconnect()
    else:
        print("Failed to connect to CAN bus")

if __name__ == '__main__':
    main()
