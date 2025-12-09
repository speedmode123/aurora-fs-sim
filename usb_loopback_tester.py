#!/usr/bin/env python3
"""
USB Loopback Test System for Device Simulator

Creates USB loopback testing for ARS, Magnetometer, and Reaction Wheel devices.
Each device sends packets to a specific USB port, and we monitor the looped-back data.
"""

import serial
import threading
import time
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from queue import Queue, Empty
import struct

logger = logging.getLogger(__name__)

@dataclass
class USBPortConfig:
    """Configuration for USB port"""
    port: str
    baud_rate: int = 115200
    data_bits: int = 8
    stop_bits: int = 1
    parity: str = "N"
    timeout: float = 1.0

@dataclass
class LoopbackTestResult:
    """Result of loopback test"""
    device_name: str
    sent_bytes: bytes
    received_bytes: bytes
    timestamp: float
    success: bool
    latency_ms: float

class USBLoopbackMonitor:
    """Monitors USB loopback ports for received data"""
    
    def __init__(self, port_configs: Dict[str, USBPortConfig]):
        self.port_configs = port_configs
        self.monitors: Dict[str, serial.Serial] = {}
        self.data_queues: Dict[str, Queue] = {}
        self.monitor_threads: Dict[str, threading.Thread] = {}
        self.running = False
        
        # Initialize queues
        for device_name in port_configs.keys():
            self.data_queues[device_name] = Queue()
    
    def start_monitoring(self) -> bool:
        """Start monitoring all USB ports"""
        try:
            for device_name, config in self.port_configs.items():
                # Open serial port for monitoring
                monitor_port = serial.Serial(
                    port=config.port,
                    baudrate=config.baud_rate,
                    bytesize=config.data_bits,
                    stopbits=config.stop_bits,
                    parity=config.parity,
                    timeout=config.timeout
                )
                
                self.monitors[device_name] = monitor_port
                
                # Start monitoring thread
                thread = threading.Thread(
                    target=self._monitor_port,
                    args=(device_name, monitor_port),
                    daemon=True
                )
                thread.start()
                self.monitor_threads[device_name] = thread
                
                logger.info(f"Started monitoring USB port {config.port} for {device_name}")
            
            self.running = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to start USB monitoring: {e}")
            return False
    
    def stop_monitoring(self):
        """Stop monitoring all USB ports"""
        self.running = False
        
        # Close all monitor ports
        for device_name, monitor in self.monitors.items():
            try:
                monitor.close()
                logger.info(f"Stopped monitoring USB port for {device_name}")
            except:
                pass
        
        # Wait for threads to finish
        for device_name, thread in self.monitor_threads.items():
            thread.join(timeout=2.0)
    
    def _monitor_port(self, device_name: str, monitor_port: serial.Serial):
        """Monitor a single USB port for incoming data"""
        logger.info(f"Monitoring USB port {monitor_port.port} for {device_name}")
        
        while self.running:
            try:
                # Read available data
                if monitor_port.in_waiting > 0:
                    data = monitor_port.read(monitor_port.in_waiting)
                    if data:
                        # Put data in queue with timestamp
                        self.data_queues[device_name].put((data, time.time()))
                        logger.debug(f"{device_name}: Received {len(data)} bytes: {data.hex().upper()}")
                
                time.sleep(0.001)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error monitoring {device_name} port: {e}")
                time.sleep(0.1)
    
    def get_received_data(self, device_name: str, timeout: float = 1.0) -> Optional[bytes]:
        """Get received data for a specific device"""
        try:
            data, timestamp = self.data_queues[device_name].get(timeout=timeout)
            return data
        except Empty:
            return None
    
    def get_all_received_data(self, timeout: float = 1.0) -> Dict[str, List[bytes]]:
        """Get all received data from all devices"""
        results = {}
        
        for device_name in self.port_configs.keys():
            device_data = []
            while True:
                data = self.get_received_data(device_name, timeout=0.1)
                if data is None:
                    break
                device_data.append(data)
            
            if device_data:
                results[device_name] = device_data
        
        return results

class USBLoopbackTester:
    """Main USB loopback test system"""
    
    def __init__(self, device_configs: Dict[str, USBPortConfig]):
        self.device_configs = device_configs
        self.monitor = USBLoopbackMonitor(device_configs)
        self.test_results: List[LoopbackTestResult] = []
        
    def start_testing(self) -> bool:
        """Start the loopback test system"""
        logger.info("Starting USB Loopback Test System")
        
        if self.monitor.start_monitoring():
            logger.info("USB Loopback Test System started successfully")
            return True
        else:
            logger.error("Failed to start USB Loopback Test System")
            return False
    
    def stop_testing(self):
        """Stop the loopback test system"""
        logger.info("Stopping USB Loopback Test System")
        self.monitor.stop_monitoring()
    
    def test_device_packet(self, device_name: str, packet_data: bytes) -> LoopbackTestResult:
        """
        Test a device packet by sending it and monitoring the loopback
        
        Args:
            device_name: Name of the device (ars, magnetometer, reaction_wheel)
            packet_data: Packet data to send
            
        Returns:
            LoopbackTestResult with test results
        """
        if device_name not in self.device_configs:
            logger.error(f"Unknown device: {device_name}")
            return LoopbackTestResult(
                device_name=device_name,
                sent_bytes=packet_data,
                received_bytes=b"",
                timestamp=time.time(),
                success=False,
                latency_ms=0.0
            )
        
        config = self.device_configs[device_name]
        start_time = time.time()
        
        try:
            # Send packet to USB port
            with serial.Serial(
                port=config.port,
                baudrate=config.baud_rate,
                bytesize=config.data_bits,
                stopbits=config.stop_bits,
                parity=config.parity,
                timeout=config.timeout
            ) as sender_port:
                
                sender_port.write(packet_data)
                sender_port.flush()
                logger.info(f"Sent {len(packet_data)} bytes to {device_name} port {config.port}")
                logger.info(f"Sent data: {packet_data.hex().upper()}")
                
                # Wait for loopback data
                time.sleep(0.1)  # Allow time for loopback
                
                # Get received data
                received_data = self.monitor.get_received_data(device_name, timeout=2.0)
                
                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000
                
                if received_data:
                    logger.info(f"Received {len(received_data)} bytes from {device_name}")
                    logger.info(f"Received data: {received_data.hex().upper()}")
                    
                    # Check if received data matches sent data
                    success = received_data == packet_data
                    
                    result = LoopbackTestResult(
                        device_name=device_name,
                        sent_bytes=packet_data,
                        received_bytes=received_data,
                        timestamp=start_time,
                        success=success,
                        latency_ms=latency_ms
                    )
                    
                    self.test_results.append(result)
                    return result
                else:
                    logger.warning(f"No data received from {device_name} loopback")
                    return LoopbackTestResult(
                        device_name=device_name,
                        sent_bytes=packet_data,
                        received_bytes=b"",
                        timestamp=start_time,
                        success=False,
                        latency_ms=latency_ms
                    )
                    
        except Exception as e:
            logger.error(f"Error testing {device_name}: {e}")
            return LoopbackTestResult(
                device_name=device_name,
                sent_bytes=packet_data,
                received_bytes=b"",
                timestamp=time.time(),
                success=False,
                latency_ms=0.0
            )
    
    def test_all_devices(self, device_packets: Dict[str, bytes]) -> Dict[str, LoopbackTestResult]:
        """Test all devices with their respective packets"""
        results = {}
        
        for device_name, packet_data in device_packets.items():
            logger.info(f"Testing {device_name} with {len(packet_data)} bytes")
            result = self.test_device_packet(device_name, packet_data)
            results[device_name] = result
            
            # Small delay between tests
            time.sleep(0.5)
        
        return results
    
    def print_test_summary(self):
        """Print summary of all test results"""
        logger.info("=== USB Loopback Test Summary ===")
        
        for result in self.test_results:
            status = "PASS" if result.success else "FAIL"
            logger.info(f"{result.device_name}: {status} - "
                       f"Sent: {len(result.sent_bytes)} bytes, "
                       f"Received: {len(result.received_bytes)} bytes, "
                       f"Latency: {result.latency_ms:.2f}ms")
            
            if result.sent_bytes:
                logger.info(f"  Sent:    {result.sent_bytes.hex().upper()}")
            if result.received_bytes:
                logger.info(f"  Received: {result.received_bytes.hex().upper()}")
            
            if not result.success and result.sent_bytes and result.received_bytes:
                logger.warning(f"  Data mismatch detected!")

def main():
    """Test USB loopback system"""
    import argparse
    
    parser = argparse.ArgumentParser(description='USB Loopback Test System')
    parser.add_argument('--ars-port', default='/dev/ttyUSB0', help='ARS USB port')
    parser.add_argument('--mag-port', default='/dev/ttyUSB1', help='Magnetometer USB port')
    parser.add_argument('--rw-port', default='/dev/ttyUSB2', help='Reaction Wheel USB port')
    parser.add_argument('--baud-rate', type=int, default=115200, help='Baud rate')
    parser.add_argument('--test-duration', type=float, default=30.0, help='Test duration in seconds')
    
    args = parser.parse_args()
    
    # Configure USB ports for each device
    device_configs = {
        'ars': USBPortConfig(port=args.ars_port, baud_rate=args.baud_rate),
        'magnetometer': USBPortConfig(port=args.mag_port, baud_rate=args.baud_rate),
        'reaction_wheel': USBPortConfig(port=args.rw_port, baud_rate=args.baud_rate)
    }
    
    # Create test system
    tester = USBLoopbackTester(device_configs)
    
    if tester.start_testing():
        try:
            logger.info(f"USB Loopback Test running for {args.test_duration} seconds")
            logger.info("Send test packets to the configured USB ports")
            
            # Run test for specified duration
            start_time = time.time()
            while time.time() - start_time < args.test_duration:
                time.sleep(1.0)
            
            # Print summary
            tester.print_test_summary()
            
        finally:
            tester.stop_testing()
    else:
        logger.error("Failed to start USB Loopback Test System")

if __name__ == '__main__':
    main()
