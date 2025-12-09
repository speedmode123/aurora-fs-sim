#!/usr/bin/env python3
"""
FlatSat Device Simulator - Main Application

Comprehensive application that receives data from MATLAB simulator via TCP/IP
and converts it to proper device packet formats for testing satellite systems.
Supports ARS, Magnetometer, and Reaction Wheel devices with multiple output interfaces.
"""

import sys
import os
import json
import time
import logging
import argparse
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from tcp_receiver import TCPReceiver, TCPConfig as TCPReceiverConfig
from device_encoders.ars_encoder import ARSEncoder
from device_encoders.magnetometer_encoder import MagnetometerEncoder
from device_encoders.reaction_wheel_encoder import ReactionWheelEncoder
from output_transmitters.serial_transmitter import SerialTransmitterManager, SerialConfig
from output_transmitters.can_transmitter import CANTransmitterManager, CANConfig
from output_transmitters.tcp_transmitter import TCPTransmitterManager, TCPConfig
from usb_loopback_tester import USBLoopbackTester, USBPortConfig
from packet_logger import PacketLogger
from error_handler import error_handler, handle_error, ErrorType, ErrorSeverity
from performance_monitor import performance_monitor, measure_performance

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('flatsat_simulator.log')
    ]
)

logger = logging.getLogger(__name__)

@dataclass
class DeviceConfig:
    """Configuration for a single device"""
    enabled: bool = False
    matlab_ports: List[int] = None
    output_mode: str = "serial"  # serial, can, tcp
    output_config: Dict[str, Any] = None
    endianness: str = "little"  # little, big
    duplicate_primary_to_redundant: bool = False  # For ARS: duplicate primary to redundant
    redundant_variation_percent: float = 0.1  # For ARS: variation percentage
    usb_loopback_enabled: bool = False  # Enable USB loopback testing
    usb_loopback_port: str = ""  # USB port for loopback testing
    log_packets_to_file: bool = False  # Log sent packets to file when loopback disabled
    packet_log_file: str = ""  # File path for packet logging
    status_cycling_enabled: bool = False  # Enable status cycling
    status_cycle_interval: float = 10.0  # Status cycle interval in seconds
    status_scenarios: List[str] = None  # List of status scenarios
    
    def __post_init__(self):
        if self.matlab_ports is None:
            self.matlab_ports = []
        if self.output_config is None:
            self.output_config = {}
        if self.status_scenarios is None:
            self.status_scenarios = ["normal"]

@dataclass
class SimulatorConfig:
    """Main simulator configuration"""
    tcp_mode: str = "server"  # server, client
    matlab_server_ip: str = "192.168.1.100"
    matlab_server_port: int = 5000
    devices: Dict[str, DeviceConfig] = None
    
    def __post_init__(self):
        if self.devices is None:
            self.devices = {}

class FlatSatDeviceSimulator:
    """Main simulator application"""
    
    def __init__(self, config: SimulatorConfig):
        self.config = config
        self.tcp_receiver: Optional[TCPReceiver] = None
        self.device_encoders: Dict[str, Any] = {}
        self.output_transmitters: Dict[str, Any] = {}
        self.usb_loopback_tester: Optional[USBLoopbackTester] = None
        self.packet_logger: Optional[PacketLogger] = None
        self.running = False
        self.threads: List[threading.Thread] = []
        
        # Initialize enabled devices
        self._initialize_devices()
        
        # Initialize packet logger and USB loopback tester
        self._initialize_logging_and_testing()
        
    def _initialize_devices(self):
        """Initialize enabled devices"""
        for device_name, device_config in self.config.devices.items():
            if device_config.enabled:
                logger.info(f"Initializing device: {device_name}")
                
                # Initialize encoder
                if device_name == "ars":
                    # Get duplication settings from device config
                    # Check if attributes exist, otherwise use defaults
                    duplicate = getattr(device_config, 'duplicate_primary_to_redundant', False)
                    variation = getattr(device_config, 'redundant_variation_percent', 0.1)
                    self.device_encoders[device_name] = ARSEncoder(
                        duplicate_to_redundant=duplicate,
                        variation_percent=variation
                    )
                    logger.info(f"ARS encoder: duplication={duplicate}, variation={variation}%")
                elif device_name == "magnetometer":
                    self.device_encoders[device_name] = MagnetometerEncoder()
                elif device_name == "reaction_wheel":
                    self.device_encoders[device_name] = ReactionWheelEncoder()
                else:
                    logger.error(f"Unknown device type: {device_name}")
                    continue
                
                # Initialize output transmitter
                self._initialize_output_transmitter(device_name, device_config)
    
    def _initialize_logging_and_testing(self):
        """Initialize packet logger and USB loopback tester based on device configurations"""
        # Check if any device needs USB loopback testing
        loopback_devices = {}
        logging_devices = {}
        
        for device_name, device_config in self.config.devices.items():
            if device_config.enabled:
                if device_config.usb_loopback_enabled and device_config.usb_loopback_port:
                    loopback_devices[device_name] = USBPortConfig(
                        port=device_config.usb_loopback_port,
                        baud_rate=device_config.output_config.get("baud_rate", 115200)
                    )
                
                if device_config.log_packets_to_file and device_config.packet_log_file:
                    logging_devices[device_name] = device_config.packet_log_file
        
        # Initialize USB loopback tester if needed
        if loopback_devices:
            logger.info(f"Initializing USB loopback tester for devices: {list(loopback_devices.keys())}")
            self.usb_loopback_tester = USBLoopbackTester(loopback_devices)
        
        # Initialize packet logger if needed
        if logging_devices:
            logger.info(f"Initializing packet logger for devices: {list(logging_devices.keys())}")
            self.packet_logger = PacketLogger()
            
            for device_name, log_file in logging_devices.items():
                self.packet_logger.setup_device_logging(device_name, log_file)
    
    def _initialize_output_transmitter(self, device_name: str, device_config: DeviceConfig):
        """Initialize output transmitter for a device"""
        output_mode = device_config.output_mode
        output_config = device_config.output_config
        
        if output_mode == "serial":
            if "serial_transmitters" not in self.output_transmitters:
                self.output_transmitters["serial_transmitters"] = SerialTransmitterManager()
            
            serial_config = SerialConfig(
                port=output_config.get("port", "/dev/ttyUSB0"),
                baud_rate=output_config.get("baud_rate", 115200)
            )
            
            self.output_transmitters["serial_transmitters"].add_transmitter(device_name, serial_config)
            
        elif output_mode == "can":
            if "can_transmitters" not in self.output_transmitters:
                self.output_transmitters["can_transmitters"] = CANTransmitterManager()
            
            can_config = CANConfig(
                interface=output_config.get("interface", "socketcan"),
                channel=output_config.get("channel", "can0"),
                bitrate=output_config.get("bitrate", 500000)
            )
            
            self.output_transmitters["can_transmitters"].add_transmitter(device_name, can_config)
            
        elif output_mode == "tcp":
            if "tcp_transmitters" not in self.output_transmitters:
                self.output_transmitters["tcp_transmitters"] = TCPTransmitterManager()
            
            tcp_config = TCPConfig(
                target_ip=output_config.get("target_ip", "192.168.1.200"),
                target_port=output_config.get("target_port", 8000)
            )
            
            self.output_transmitters["tcp_transmitters"].add_transmitter(device_name, tcp_config)
            
        else:
            logger.error(f"Unknown output mode: {output_mode}")
    
    def start(self):
        """Start the simulator"""
        logger.info("Starting FlatSat Device Simulator")
        
        # Start TCP receiver
        self._start_tcp_receiver()
        
        # Start USB loopback tester if needed
        self._start_usb_loopback_tester()
        
        # Start performance monitoring
        performance_monitor.start_monitoring()
        
        # Start data processing threads
        self._start_data_processing()
        
        self.running = True
        logger.info("FlatSat Device Simulator started successfully")
    
    def _start_tcp_receiver(self):
        """Start TCP receiver"""
        tcp_config = TCPReceiverConfig(
            mode=self.config.tcp_mode,
            ip_address=self.config.matlab_server_ip,
            port=self.config.matlab_server_port
        )
        
        self.tcp_receiver = TCPReceiver(tcp_config)
        
        if self.tcp_receiver.start():
            # Configure devices after starting
            device_configs = {}
            for device_name, device_config in self.config.devices.items():
                if device_config.enabled:
                    device_configs[device_name] = {
                        'enabled': device_config.enabled,
                        'matlab_ports': device_config.matlab_ports
                    }
            
            self.tcp_receiver.configure_devices(device_configs)
            logger.info("TCP receiver started successfully")
        else:
            logger.error("Failed to start TCP receiver")
            raise RuntimeError("Failed to start TCP receiver")
    
    def _start_usb_loopback_tester(self):
        """Start USB loopback tester if any device has it enabled"""
        if self.usb_loopback_tester:
            if self.usb_loopback_tester.start_testing():
                logger.info("USB loopback tester started successfully")
            else:
                logger.warning("Failed to start USB loopback tester")
    
    def _start_data_processing(self):
        """Start data processing threads for each device"""
        for device_name, device_config in self.config.devices.items():
            if device_config.enabled:
                thread = threading.Thread(
                    target=self._process_device_data,
                    args=(device_name, device_config),
                    daemon=True
                )
                thread.start()
                self.threads.append(thread)
                logger.info(f"Started data processing thread for {device_name}")
    
    def _process_device_data(self, device_name: str, device_config: DeviceConfig):
        """Process data for a specific device"""
        encoder = self.device_encoders.get(device_name)
        if not encoder:
            logger.error(f"No encoder found for device {device_name}")
            return
        
        while self.running:
            try:
                # Get data from TCP receiver
                with measure_performance(f"{device_name}_receiver", "get_data"):
                    data = self.tcp_receiver.get_data(device_name)
                
                if data:
                    # Process data based on device type
                    with measure_performance(f"{device_name}_encoder", "encode_data"):
                        encoded_data = self._encode_device_data(device_name, encoder, data, device_config)
                    
                    if encoded_data:
                        # Send to output transmitter
                        with measure_performance(f"{device_name}_transmitter", "send_data"):
                            self._send_to_output(device_name, device_config, encoded_data)
                
                time.sleep(0.001)  # Small delay to prevent busy waiting
                
            except Exception as e:
                if not handle_error(e, device_name, "data_processor", "process_data", 
                                  ErrorType.DATA_PROCESSING, ErrorSeverity.MEDIUM):
                    logger.error(f"Critical error processing data for {device_name}, stopping thread")
                    break
                time.sleep(0.1)
    
    def _encode_device_data(self, device_name: str, encoder: Any, data: List[float], device_config: DeviceConfig) -> Optional[bytes]:
        """Encode device data based on device type and output mode"""
        try:
            if device_name == "ars":
                return encoder.process_matlab_data(data)
            elif device_name == "magnetometer":
                output_mode = device_config.output_mode
                if output_mode == "can":
                    result = encoder.process_matlab_data_can(data)
                    if result:
                        can_id, encoded_data = result
                        # For CAN, we need to return both ID and data
                        return f"{can_id}:{encoded_data.hex()}".encode()
                    return None
                else:  # rs485
                    return encoder.process_matlab_data_rs485(data)
            elif device_name == "reaction_wheel":
                # Default to health status telemetry
                return encoder.process_matlab_data_health(data)
            else:
                logger.error(f"Unknown device type: {device_name}")
                return None
                
        except Exception as e:
            handle_error(e, device_name, "encoder", "encode_data", 
                        ErrorType.ENCODING, ErrorSeverity.HIGH)
            return None
    
    def _send_to_output(self, device_name: str, device_config: DeviceConfig, encoded_data: bytes):
        """Send encoded data to output transmitter"""
        output_mode = device_config.output_mode
        
        # Log packet if logging is enabled
        if device_config.log_packets_to_file and self.packet_logger:
            self.packet_logger.log_packet(device_name, encoded_data)
        
        # Test USB loopback if enabled
        if device_config.usb_loopback_enabled and self.usb_loopback_tester:
            self.usb_loopback_tester.test_device_packet(device_name, encoded_data)
        
        try:
            if output_mode == "serial":
                transmitter_manager = self.output_transmitters.get("serial_transmitters")
                if transmitter_manager:
                    transmitter_manager.send_data(device_name, encoded_data)
                    
            elif output_mode == "can":
                transmitter_manager = self.output_transmitters.get("can_transmitters")
                if transmitter_manager:
                    # Parse CAN ID and data
                    if b":" in encoded_data:
                        can_id_str, data_hex = encoded_data.split(b":", 1)
                        can_id = int(can_id_str.decode())
                        data_bytes = bytes.fromhex(data_hex.decode())
                        transmitter_manager.send_message(device_name, can_id, data_bytes)
                    
            elif output_mode == "tcp":
                transmitter_manager = self.output_transmitters.get("tcp_transmitters")
                if transmitter_manager:
                    transmitter_manager.send_data(device_name, encoded_data)
                    
        except Exception as e:
            handle_error(e, device_name, "transmitter", "send_data", 
                        ErrorType.TRANSMISSION, ErrorSeverity.MEDIUM)
    
    def stop(self):
        """Stop the simulator"""
        logger.info("Stopping FlatSat Device Simulator")
        self.running = False
        
        # Stop TCP receiver
        if self.tcp_receiver:
            self.tcp_receiver.stop()
        
        # Stop output transmitters
        for transmitter_manager in self.output_transmitters.values():
            if hasattr(transmitter_manager, 'disconnect_all'):
                transmitter_manager.disconnect_all()
        
        # Stop USB loopback tester
        if self.usb_loopback_tester:
            self.usb_loopback_tester.stop_testing()
        
        # Close packet logger
        if self.packet_logger:
            self.packet_logger.close_all_logging()
        
        # Stop performance monitoring
        performance_monitor.stop_monitoring()
        
        # Wait for threads to finish
        for thread in self.threads:
            thread.join(timeout=2.0)
        
        # Print error statistics
        error_stats = error_handler.get_error_statistics()
        if error_stats["total_errors"] > 0:
            logger.info(f"Error Statistics: {error_stats['total_errors']} total errors, "
                       f"{error_stats['recovered_errors']} recovered, "
                       f"{error_stats['recovery_rate']:.1f}% recovery rate")
        
        # Print performance statistics
        perf_summary = performance_monitor.get_performance_summary()
        logger.info(f"Performance Summary: {perf_summary['system_metrics']['total_packets']} packets processed, "
                   f"CPU: {perf_summary['system_metrics']['cpu_usage']:.1f}%, "
                   f"Memory: {perf_summary['system_metrics']['memory_usage']:.1f}%")
        
        logger.info("FlatSat Device Simulator stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get simulator status"""
        status = {
            "running": self.running,
            "tcp_receiver": self.tcp_receiver.get_status() if self.tcp_receiver else None,
            "output_transmitters": {}
        }
        
        for transmitter_type, transmitter_manager in self.output_transmitters.items():
            if hasattr(transmitter_manager, 'get_status'):
                status["output_transmitters"][transmitter_type] = transmitter_manager.get_status()
        
        return status

def load_config(config_file: str) -> SimulatorConfig:
    """Load configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Parse device configurations
        devices = {}
        for device_name, device_data in config_data.get("devices", {}).items():
            device_config = DeviceConfig(
                enabled=device_data.get("enabled", False),
                matlab_ports=device_data.get("matlab_ports", []),
                output_mode=device_data.get("output_mode", "serial"),
                output_config=device_data.get("output_config", {}),
                endianness=device_data.get("endianness", "little"),
                duplicate_primary_to_redundant=device_data.get("duplicate_primary_to_redundant", False),
                redundant_variation_percent=device_data.get("redundant_variation_percent", 0.1),
                usb_loopback_enabled=device_data.get("usb_loopback_enabled", False),
                usb_loopback_port=device_data.get("usb_loopback_port", ""),
                log_packets_to_file=device_data.get("log_packets_to_file", False),
                packet_log_file=device_data.get("packet_log_file", ""),
                status_cycling_enabled=device_data.get("status_cycling_enabled", False),
                status_cycle_interval=device_data.get("status_cycle_interval", 10.0),
                status_scenarios=device_data.get("status_scenarios", ["normal"])
            )
            devices[device_name] = device_config
        
        # Create main configuration
        config = SimulatorConfig(
            tcp_mode=config_data.get("tcp_mode", "server"),
            matlab_server_ip=config_data.get("matlab_server_ip", "192.168.1.100"),
            matlab_server_port=config_data.get("matlab_server_port", 5000),
            devices=devices
        )
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to load configuration from {config_file}: {e}")
        raise

def create_default_config() -> SimulatorConfig:
    """Create default configuration"""
    devices = {
        "ars": DeviceConfig(
            enabled=True,
            matlab_ports=list(range(5000, 5012)),  # 12 ports
            output_mode="serial",
            output_config={"port": "/dev/ttyUSB0", "baud_rate": 115200},
            endianness="little"
        ),
        "magnetometer": DeviceConfig(
            enabled=True,
            matlab_ports=[6000, 6001, 6002],  # 3 ports
            output_mode="can",
            output_config={"interface": "socketcan", "channel": "can0", "bitrate": 500000},
            endianness="little"
        ),
        "reaction_wheel": DeviceConfig(
            enabled=False,
            matlab_ports=[7000, 7001, 7002, 7003],  # 4 ports
            output_mode="tcp",
            output_config={"target_ip": "192.168.1.200", "target_port": 8000},
            endianness="little"
        )
    }
    
    return SimulatorConfig(
        tcp_mode="server",
        matlab_server_ip="192.168.1.100",
        matlab_server_port=5000,
        devices=devices
    )

def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description='FlatSat Device Simulator')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--enable-ars', action='store_true', help='Enable ARS device')
    parser.add_argument('--enable-mag', action='store_true', help='Enable Magnetometer device')
    parser.add_argument('--enable-rw', action='store_true', help='Enable Reaction Wheel device')
    parser.add_argument('--ars-output', choices=['serial', 'can', 'tcp'], help='ARS output mode')
    parser.add_argument('--mag-output', choices=['serial', 'can', 'tcp'], help='Magnetometer output mode')
    parser.add_argument('--rw-output', choices=['serial', 'can', 'tcp'], help='Reaction Wheel output mode')
    parser.add_argument('--tcp-mode', choices=['server', 'client'], help='TCP mode')
    parser.add_argument('--listen-port', type=int, help='TCP listen port')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--log-file', help='Log file path')
    
    args = parser.parse_args()
    
    # Configure logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(file_handler)
    
    try:
        # Load configuration
        if args.config:
            config = load_config(args.config)
        else:
            config = create_default_config()
        
        # Override with command line arguments
        if args.enable_ars:
            config.devices["ars"].enabled = True
        if args.enable_mag:
            config.devices["magnetometer"].enabled = True
        if args.enable_rw:
            config.devices["reaction_wheel"].enabled = True
        
        if args.ars_output:
            config.devices["ars"].output_mode = args.ars_output
        if args.mag_output:
            config.devices["magnetometer"].output_mode = args.mag_output
        if args.rw_output:
            config.devices["reaction_wheel"].output_mode = args.rw_output
        
        if args.tcp_mode:
            config.tcp_mode = args.tcp_mode
        if args.listen_port:
            config.matlab_server_port = args.listen_port
        
        # Create and start simulator
        simulator = FlatSatDeviceSimulator(config)
        
        try:
            simulator.start()
            
            # Keep running until interrupted
            while True:
                time.sleep(1.0)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            simulator.stop()
            
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
