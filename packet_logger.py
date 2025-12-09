#!/usr/bin/env python3
"""
Packet Logger for Device Simulator

Logs device packets to files when USB loopback is not available.
Provides hex format logging with timestamps for analysis.
"""

import os
import time
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class PacketLogger:
    """Logs device packets to files"""
    
    def __init__(self, log_directory: str = "packet_logs"):
        self.log_directory = log_directory
        self.log_files: Dict[str, str] = {}
        self.log_handles: Dict[str, object] = {}
        
        # Create log directory if it doesn't exist
        os.makedirs(log_directory, exist_ok=True)
        
        logger.info(f"Packet logger initialized with directory: {log_directory}")
    
    def setup_device_logging(self, device_name: str, log_file: str) -> bool:
        """Setup logging for a specific device"""
        try:
            # Create full path
            full_path = os.path.join(self.log_directory, log_file)
            
            # Open log file
            log_handle = open(full_path, 'w')
            log_handle.write(f"# Packet Log for {device_name.upper()}\n")
            log_handle.write(f"# Started: {datetime.now().isoformat()}\n")
            log_handle.write(f"# Format: TIMESTAMP | PACKET_SIZE | HEX_DATA\n")
            log_handle.write(f"# {'='*80}\n")
            log_handle.flush()
            
            self.log_files[device_name] = full_path
            self.log_handles[device_name] = log_handle
            
            logger.info(f"Packet logging enabled for {device_name}: {full_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup logging for {device_name}: {e}")
            return False
    
    def log_packet(self, device_name: str, packet_data: bytes) -> bool:
        """Log a packet for a specific device"""
        if device_name not in self.log_handles:
            return False
        
        try:
            log_handle = self.log_handles[device_name]
            timestamp = datetime.now().isoformat()
            hex_data = packet_data.hex().upper()
            
            # Write log entry
            log_handle.write(f"{timestamp} | {len(packet_data):4d} | {hex_data}\n")
            log_handle.flush()
            
            logger.debug(f"Logged {len(packet_data)} bytes for {device_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log packet for {device_name}: {e}")
            return False
    
    def close_device_logging(self, device_name: str):
        """Close logging for a specific device"""
        if device_name in self.log_handles:
            try:
                log_handle = self.log_handles[device_name]
                log_handle.write(f"# Logging stopped: {datetime.now().isoformat()}\n")
                log_handle.close()
                del self.log_handles[device_name]
                logger.info(f"Closed packet logging for {device_name}")
            except Exception as e:
                logger.error(f"Error closing log for {device_name}: {e}")
    
    def close_all_logging(self):
        """Close all device logging"""
        for device_name in list(self.log_handles.keys()):
            self.close_device_logging(device_name)
        logger.info("All packet logging closed")
    
    def get_log_summary(self) -> Dict[str, Dict[str, any]]:
        """Get summary of all log files"""
        summary = {}
        
        for device_name, log_file in self.log_files.items():
            try:
                if os.path.exists(log_file):
                    stat = os.stat(log_file)
                    summary[device_name] = {
                        "log_file": log_file,
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "active": device_name in self.log_handles
                    }
                else:
                    summary[device_name] = {
                        "log_file": log_file,
                        "size_bytes": 0,
                        "modified": "N/A",
                        "active": False
                    }
            except Exception as e:
                logger.error(f"Error getting summary for {device_name}: {e}")
                summary[device_name] = {
                    "log_file": log_file,
                    "error": str(e),
                    "active": False
                }
        
        return summary

def main():
    """Test packet logger"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Packet Logger Test')
    parser.add_argument('--log-dir', default='packet_logs', help='Log directory')
    parser.add_argument('--test-duration', type=float, default=10.0, help='Test duration')
    
    args = parser.parse_args()
    
    # Create packet logger
    logger_system = PacketLogger(args.log_dir)
    
    # Setup logging for test devices
    test_devices = ['ars', 'magnetometer', 'reaction_wheel']
    for device in test_devices:
        logger_system.setup_device_logging(device, f"{device}_packets.log")
    
    try:
        logger.info(f"Testing packet logger for {args.test_duration} seconds")
        
        # Generate test packets
        start_time = time.time()
        packet_count = 0
        
        while time.time() - start_time < args.test_duration:
            for device in test_devices:
                # Generate test packet (varying size)
                test_packet = bytes([i % 256 for i in range(20 + packet_count % 50)])
                
                # Log packet
                logger_system.log_packet(device, test_packet)
                packet_count += 1
            
            time.sleep(0.1)  # 100ms between packets
        
        # Print summary
        logger.info("=== Packet Log Summary ===")
        summary = logger_system.get_log_summary()
        for device, info in summary.items():
            logger.info(f"{device}: {info['size_bytes']} bytes, "
                       f"Modified: {info['modified']}, "
                       f"Active: {info['active']}")
        
    finally:
        logger_system.close_all_logging()

if __name__ == '__main__':
    main()
