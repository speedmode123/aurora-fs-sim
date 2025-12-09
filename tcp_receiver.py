#!/usr/bin/env python3
"""
TCP/IP Receiver for MATLAB Device Simulator

Receives 8-byte float data from MATLAB simulator via TCP/IP and distributes
to device encoders. Supports both server and client modes.
"""

import socket
import struct
import threading
import time
import logging
from typing import Dict, List, Optional, Callable, Tuple, Any
from dataclasses import dataclass
from collections import deque
from queue import Queue, Empty

# Import raw data logger
try:
    from raw_data_logger import RawDataLogger
except ImportError:
    RawDataLogger = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TCPConfig:
    """Configuration for TCP receiver"""
    mode: str  # 'server' or 'client'
    ip_address: str
    port: int
    is_big_endian: bool = False  # Configurable endianness
    buffer_size: int = 8192
    timeout: float = 1.0
    reconnect_delay: float = 5.0

class TCPPortReceiver:
    """Handles TCP connection for a single port"""
    
    def __init__(self, config: TCPConfig, port_index: int, data_callback: Callable):
        self.config = config
        self.port_index = port_index
        self.data_callback = data_callback
        self.socket: Optional[socket.socket] = None
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.data_queue = Queue(maxsize=1000)
        self.stats = {
            'packets_received': 0,
            'bytes_received': 0,
            'parse_errors': 0,
            'last_receive_time': 0
        }
        
    def start(self):
        """Start the TCP receiver"""
        self.is_running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"Started TCP receiver for port {self.config.port}")
        
    def stop(self):
        """Stop the TCP receiver"""
        self.is_running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        if self.thread:
            self.thread.join(timeout=2.0)
        logger.info(f"Stopped TCP receiver for port {self.config.port}")
        
    def _connect(self) -> bool:
        """Establish TCP connection"""
        try:
            if self.config.mode == 'server':
                # Server mode: listen for connections
                server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_socket.bind((self.config.ip_address, self.config.port))
                server_socket.listen(1)
                server_socket.settimeout(self.config.timeout)
                
                logger.info(f"Listening on {self.config.ip_address}:{self.config.port}")
                
                while self.is_running:
                    try:
                        self.socket, addr = server_socket.accept()
                        logger.info(f"Accepted connection from {addr} on port {self.config.port}")
                        self.socket.settimeout(self.config.timeout)
                        return True
                    except socket.timeout:
                        continue
                    except Exception as e:
                        logger.error(f"Accept error on port {self.config.port}: {e}")
                        time.sleep(1.0)
                        
            else:  # client mode
                # Client mode: connect to server
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self.config.timeout)
                self.socket.connect((self.config.ip_address, self.config.port))
                logger.info(f"Connected to {self.config.ip_address}:{self.config.port}")
                return True
                
        except Exception as e:
            logger.error(f"Connection error on port {self.config.port}: {e}")
            return False
            
        return False
    
    def _parse_float(self, data: bytes) -> Optional[float]:
        """Parse 8-byte float with configurable endianness"""
        if len(data) != 8:
            self.stats['parse_errors'] += 1
            return None
            
        try:
            if self.config.is_big_endian:
                value = struct.unpack('>d', data)[0]
            else:
                value = struct.unpack('<d', data)[0]
                
            # Validate float
            if value != value or abs(value) == float('inf'):  # NaN or infinity
                self.stats['parse_errors'] += 1
                return None
                
            return value
        except struct.error as e:
            logger.error(f"Parse error on port {self.config.port}: {e}")
            self.stats['parse_errors'] += 1
            return None
    
    def _run(self):
        """Main receiver loop - reads exactly 8 bytes at a time to preserve timing"""
        while self.is_running:
            # Connect or reconnect
            if not self.socket or not self._is_connected():
                if not self._connect():
                    logger.warning(f"Failed to connect on port {self.config.port}, retrying in {self.config.reconnect_delay}s")
                    time.sleep(self.config.reconnect_delay)
                    continue
            
            try:
                # Read exactly 8 bytes for one float
                float_bytes = b''
                while len(float_bytes) < 8 and self.is_running:
                    chunk = self.socket.recv(8 - len(float_bytes))
                    if not chunk:
                        # Connection closed
                        logger.warning(f"Connection closed on port {self.config.port}")
                        if self.socket:
                            self.socket.close()
                            self.socket = None
                        break
                    float_bytes += chunk
                
                if len(float_bytes) == 8:
                    # Log actual data size received for debugging
                    logger.debug(f"Received exactly 8 bytes on port {self.config.port}")
                    
                    self.stats['bytes_received'] += 8
                    
                    # Parse the 8-byte float
                    float_value = self._parse_float(float_bytes)
                    if float_value is not None:
                        self.stats['packets_received'] += 1
                        self.stats['last_receive_time'] = time.time()
                        
                        # Add to queue and call callback
                        try:
                            self.data_queue.put_nowait(float_value)
                            self.data_callback(self.port_index, float_value)
                        except:
                            pass  # Queue full, drop data
                            
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Receive error on port {self.config.port}: {e}")
                if self.socket:
                    self.socket.close()
                    self.socket = None
                time.sleep(1.0)
    
    def _is_connected(self) -> bool:
        """Check if socket is connected"""
        if not self.socket:
            return False
        try:
            # Simple check - try to get socket error status
            error = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            return error == 0
        except:
            return False
    
    def get_stats(self) -> Dict:
        """Get receiver statistics"""
        return dict(self.stats)

class MATLABTCPReceiver:
    """Main TCP receiver managing multiple ports for devices"""
    
    def __init__(self, device_configs: Dict[str, Dict]):
        """
        Initialize receiver with device configurations
        
        device_configs format:
        {
            'ars': {
                'tcp_mode': 'server',
                'ip': '0.0.0.0',
                'start_port': 5000,
                'num_ports': 12,
                'is_big_endian': False
            },
            'magnetometer': {...},
            'reaction_wheel': {...}
        }
        """
        self.device_configs = device_configs
        self.receivers: Dict[str, List[TCPPortReceiver]] = {}
        self.device_data: Dict[str, List[float]] = {}
        self.data_callbacks: Dict[str, Callable] = {}
        self.is_running = False
        
    def register_device_callback(self, device_name: str, callback: Callable):
        """Register a callback for when device data is received"""
        self.data_callbacks[device_name] = callback
        
    def start(self):
        """Start all TCP receivers"""
        self.is_running = True
        
        for device_name, config in self.device_configs.items():
            if not config.get('enabled', True):
                continue
                
            self.receivers[device_name] = []
            self.device_data[device_name] = [0.0] * config.get('num_ports', 1)
            
            start_port = config.get('start_port', 5000)
            num_ports = config.get('num_ports', 1)
            
            for i in range(num_ports):
                port_config = TCPConfig(
                    mode=config.get('tcp_mode', 'server'),
                    ip_address=config.get('ip', '0.0.0.0'),
                    port=start_port + i,
                    is_big_endian=config.get('is_big_endian', False)
                )
                
                def make_callback(dev_name, port_idx):
                    def callback(idx, value):
                        self._on_data_received(dev_name, port_idx, value)
                    return callback
                
                receiver = TCPPortReceiver(
                    port_config,
                    i,
                    make_callback(device_name, i)
                )
                receiver.start()
                self.receivers[device_name].append(receiver)
            
            logger.info(f"Started {num_ports} TCP receivers for {device_name} on ports {start_port}-{start_port+num_ports-1}")
    
    def stop(self):
        """Stop all TCP receivers"""
        self.is_running = False
        
        for device_name, receivers in self.receivers.items():
            for receiver in receivers:
                receiver.stop()
        
        logger.info("Stopped all TCP receivers")
    
    def _on_data_received(self, device_name: str, port_index: int, value: float):
        """Handle received data"""
        if device_name in self.device_data:
            self.device_data[device_name][port_index] = value
            
            # Call device-specific callback if registered
            if device_name in self.data_callbacks:
                try:
                    self.data_callbacks[device_name](port_index, value, self.device_data[device_name])
                except Exception as e:
                    logger.error(f"Error in {device_name} callback: {e}")
    
    def get_device_data(self, device_name: str) -> List[float]:
        """Get latest data for a device"""
        return self.device_data.get(device_name, [])
    
    def get_stats(self) -> Dict:
        """Get statistics for all receivers"""
        stats = {}
        for device_name, receivers in self.receivers.items():
            device_stats = []
            for i, receiver in enumerate(receivers):
                device_stats.append({
                    'port_index': i,
                    'port': receiver.config.port,
                    **receiver.get_stats()
                })
            stats[device_name] = device_stats
        return stats

class TCPReceiver:
    """Simplified TCP receiver interface for the main simulator"""
    
    def __init__(self, config: TCPConfig):
        self.config = config
        self.matlab_receiver: Optional[MATLABTCPReceiver] = None
        self.device_data: Dict[str, List[float]] = {}
        self.device_port_mapping: Dict[str, List[int]] = {}
        
        # Initialize raw data logger
        self.raw_data_logger = None
        if RawDataLogger:
            self.raw_data_logger = RawDataLogger("raw_data_logs")
        
    def start(self) -> bool:
        """Start the TCP receiver"""
        try:
            # Create device configuration for MATLABTCPReceiver
            # This will be configured by the main simulator with actual device ports
            device_configs = {
                'tcp_receiver': {
                    'enabled': True,
                    'tcp_mode': self.config.mode,
                    'ip': self.config.ip_address,
                    'start_port': self.config.port,
                    'num_ports': 1,  # Will be updated by configure_devices
                    'is_big_endian': self.config.is_big_endian
                }
            }
            
            self.matlab_receiver = MATLABTCPReceiver(device_configs)
            self.matlab_receiver.start()
            
            logger.info(f"TCP Receiver started in {self.config.mode} mode on {self.config.ip_address}:{self.config.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start TCP receiver: {e}")
            return False
    
    def configure_devices(self, device_configs: Dict[str, Dict]):
        """Configure which devices and ports to listen for"""
        self.device_port_mapping = {}
        
        # Create new device configuration for MATLABTCPReceiver
        matlab_configs = {}
        
        for device_name, config in device_configs.items():
            if not config.get('enabled', False):
                continue
                
            ports = config.get('matlab_ports', [])
            if not ports:
                continue
                
            self.device_port_mapping[device_name] = ports
            self.device_data[device_name] = [0.0] * len(ports)
            
            # Create MATLABTCPReceiver config for this device
            matlab_configs[device_name] = {
                'enabled': True,
                'tcp_mode': self.config.mode,
                'ip': self.config.ip_address,
                'start_port': ports[0],
                'num_ports': len(ports),
                'is_big_endian': self.config.is_big_endian
            }
        
        # Setup raw data logging for each device
        if self.raw_data_logger:
            for device_name in self.device_port_mapping.keys():
                self.raw_data_logger.setup_device_logging(device_name, f"{device_name}_raw_data.log")
        
        if matlab_configs:
            # Restart with new configuration
            if self.matlab_receiver:
                self.matlab_receiver.stop()
            
            self.matlab_receiver = MATLABTCPReceiver(matlab_configs)
            
            # Register callbacks for each device
            for device_name in matlab_configs.keys():
                # Initialize device_data for this device
                if device_name in self.device_port_mapping:
                    num_ports = len(self.device_port_mapping[device_name])
                    self.device_data[device_name] = [0.0] * num_ports
                    logger.info(f"📝 Initialized {device_name} device_data with {num_ports} ports")
                
                def make_callback(dev_name):
                    def callback(port_index: int, value: float, all_values: List[float]):
                        # Store data directly in TCPReceiver.device_data (not MATLABTCPReceiver.device_data)
                        if dev_name in self.device_port_mapping:
                            ports = self.device_port_mapping[dev_name]
                            if port_index < len(ports):
                                actual_port = ports[port_index]
                                self.device_data[dev_name][port_index] = value
                                
                                # Log raw data if logger is available
                                if self.raw_data_logger:
                                    # Convert float back to bytes for logging
                                    import struct
                                    raw_bytes = struct.pack('<d', value)
                                    self.raw_data_logger.log_raw_data(dev_name, actual_port, raw_bytes, value)
                    return callback
                
                self.matlab_receiver.register_device_callback(device_name, make_callback(device_name))
            
            self.matlab_receiver.start()
            logger.info(f"TCP Receiver configured for devices: {list(matlab_configs.keys())}")
    
    def stop(self):
        """Stop the TCP receiver"""
        if self.matlab_receiver:
            self.matlab_receiver.stop()
            logger.info("TCP Receiver stopped")
        
        # Close raw data logging
        if self.raw_data_logger:
            self.raw_data_logger.close_all_logging()
    
    def get_data(self, device_name: str) -> Optional[List[float]]:
        """Get data for specified device"""
        data = self.device_data.get(device_name)
        if data:
            non_zero_count = sum(1 for x in data if abs(x) > 1e-10)
            logger.info(f"🔍 get_data({device_name}): {non_zero_count}/12 non-zero values, sample: {[f'{x:.6f}' for x in data[:3]]}")
        else:
            logger.debug(f"🔍 get_data({device_name}): No data available")
        return data
    
    def get_status(self) -> Dict[str, Any]:
        """Get receiver status"""
        if self.matlab_receiver:
            stats = self.matlab_receiver.get_stats()
            return {
                "running": True,
                "mode": self.config.mode,
                "ip": self.config.ip_address,
                "port": self.config.port,
                "devices": list(self.device_port_mapping.keys()),
                "stats": stats
            }
        return {
            "running": False,
            "mode": self.config.mode,
            "ip": self.config.ip_address,
            "port": self.config.port,
            "devices": []
        }

def main():
    """Test TCP receiver"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MATLAB TCP Receiver Test')
    parser.add_argument('--mode', choices=['server', 'client'], default='server')
    parser.add_argument('--ip', default='0.0.0.0')
    parser.add_argument('--start-port', type=int, default=5000)
    parser.add_argument('--num-ports', type=int, default=3)
    parser.add_argument('--big-endian', action='store_true', help='Use big-endian float format')
    
    args = parser.parse_args()
    
    # Test configuration
    device_configs = {
        'test_device': {
            'enabled': True,
            'tcp_mode': args.mode,
            'ip': args.ip,
            'start_port': args.start_port,
            'num_ports': args.num_ports,
            'is_big_endian': args.big_endian
        }
    }
    
    def test_callback(port_index, value, all_values):
        print(f"Port {port_index}: {value:.6f} | All: {[f'{v:.6f}' for v in all_values]}")
    
    receiver = MATLABTCPReceiver(device_configs)
    receiver.register_device_callback('test_device', test_callback)
    
    try:
        receiver.start()
        print(f"TCP Receiver running in {args.mode} mode on ports {args.start_port}-{args.start_port+args.num_ports-1}")
        print(f"Endianness: {'Big' if args.big_endian else 'Little'}")
        print("Press Ctrl+C to stop")
        
        # Monitor and print stats
        while True:
            time.sleep(10)
            stats = receiver.get_stats()
            print("\n=== Statistics ===")
            for device, device_stats in stats.items():
                for port_stat in device_stats:
                    print(f"Port {port_stat['port']}: {port_stat['packets_received']} packets, "
                          f"{port_stat['parse_errors']} errors")
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        receiver.stop()

if __name__ == '__main__':
    main()

