#!/usr/bin/env python3
"""
MATLAB Bridge - Direct Port Sender
Sends simulated MATLAB data directly to all device ports:
- ARS ports (50038-50049)
- Magnetometer ports (50050-50052) 
- Reaction Wheel ports (50053-50056)
"""

import socket
import time
import struct
import threading
import random
import math
import logging
from datetime import datetime
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MATLABBridgeSender:
    """Sends simulated MATLAB data to all device ports (ARS, Magnetometer, Reaction Wheel)"""
    
    def __init__(self, ars_ports: List[int], mag_ports: List[int], rw_ports: List[int], host: str = "127.0.0.1"):
        self.ars_ports = ars_ports
        self.mag_ports = mag_ports
        self.rw_ports = rw_ports
        self.all_ports = ars_ports + mag_ports + rw_ports
        self.host = host
        self.sockets = {}
        self.running = False
        self.start_time = None
        
    def connect_to_ports(self):
        """Connect to all specified ports"""
        logger.info(f"Connecting to {len(self.all_ports)} ports:")
        logger.info(f"  ARS ports: {self.ars_ports}")
        logger.info(f"  Magnetometer ports: {self.mag_ports}")
        logger.info(f"  Reaction Wheel ports: {self.rw_ports}")
        
        for port in self.all_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.host, port))
                self.sockets[port] = sock
                logger.info(f"✅ Connected to port {port}")
            except Exception as e:
                logger.error(f"❌ Failed to connect to port {port}: {e}")
        
        if not self.sockets:
            logger.error("No connections established. Exiting.")
            return False
        return True
    
    def generate_realistic_device_data(self, port: int, time_offset: float) -> float:
        """Generate realistic device data based on port and device type"""
        
        # ARS ports (50038-50049): Angular rates and positions
        if port in self.ars_ports:
            port_index = self.ars_ports.index(port)
            if port_index < 6:  # Ports 50038-50043: Angular rates
                base_rate = 0.0001  # 0.1 mrad/s
                variation = base_rate * 0.5 * (random.random() - 0.5)
                time_variation = base_rate * 0.3 * (math.sin(time_offset * 0.1 + port_index))
                value = variation + time_variation
            else:  # Ports 50044-50049: Angular positions
                base_angle = 0.001  # 1 mrad
                variation = base_angle * 0.5 * (random.random() - 0.5)
                time_variation = base_angle * 0.3 * (math.sin(time_offset * 0.05 + port_index))
                value = variation + time_variation
        
        # Magnetometer ports (50050-50052): Magnetic field components (Tesla)
        elif port in self.mag_ports:
            port_index = self.mag_ports.index(port)
            # Earth's magnetic field is typically 20-60 microTesla
            base_field = 4e-5  # 40 microTesla
            variation = base_field * 0.1 * (random.random() - 0.5)
            time_variation = base_field * 0.05 * (math.sin(time_offset * 0.02 + port_index))
            value = base_field + variation + time_variation
        
        # Reaction Wheel ports (50053-50056): Speed and torque
        elif port in self.rw_ports:
            port_index = self.rw_ports.index(port)
            if port_index < 2:  # Ports 50053-50054: Wheel speed (rad/s)
                base_speed = 100.0  # 100 rad/s typical wheel speed
                variation = base_speed * 0.1 * (random.random() - 0.5)
                time_variation = base_speed * 0.05 * (math.sin(time_offset * 0.1 + port_index))
                value = base_speed + variation + time_variation
            else:  # Ports 50055-50056: Wheel torque (Nm)
                base_torque = 0.01  # 0.01 Nm typical torque
                variation = base_torque * 0.2 * (random.random() - 0.5)
                time_variation = base_torque * 0.1 * (math.sin(time_offset * 0.15 + port_index))
                value = variation + time_variation
        
        else:
            # Default for unknown ports
            value = random.uniform(-0.001, 0.001)
        
        return value
    
    def _get_device_type(self, port: int) -> str:
        """Get device type for a given port"""
        if port in self.ars_ports:
            return "ARS"
        elif port in self.mag_ports:
            return "Magnetometer"
        elif port in self.rw_ports:
            return "Reaction Wheel"
        else:
            return "Unknown"
    
    def send_data_to_port(self, port: int, data: float):
        """Send float data to a specific port"""
        if port not in self.sockets:
            return False
        
        try:
            # Pack float as 8-byte double (little endian)
            data_bytes = struct.pack('<d', data)
            self.sockets[port].sendall(data_bytes)
            return True
        except Exception as e:
            logger.error(f"Error sending data to port {port}: {e}")
            return False
    
    def run_simulation(self, duration: float = 60.0):
        """Run the simulation for specified duration"""
        logger.info(f"🚀 Starting MATLAB bridge simulation for {duration} seconds")
        logger.info(f"📡 Sending data to {len(self.all_ports)} ports")
        
        if not self.connect_to_ports():
            return
        
        self.running = True
        self.start_time = time.time()
        
        try:
            packet_count = 0
            while self.running and (time.time() - self.start_time) < duration:
                current_time = time.time() - self.start_time
                
                # Send data to all ports
                for port in self.all_ports:
                    # Generate realistic device data
                    float_value = self.generate_realistic_device_data(port, current_time)
                    
                    # Send data
                    if self.send_data_to_port(port, float_value):
                        packet_count += 1
                        
                        # Log every 100 packets to avoid spam
                        if packet_count % 100 == 0:
                            device_type = self._get_device_type(port)
                            logger.info(f"📡 Sent packet {packet_count} to {device_type} port {port}: {float_value:.6f}")
                
                # Send at approximately 10 Hz (100ms intervals)
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Simulation interrupted by user")
        finally:
            self.running = False
            logger.info("✅ Simulation completed")
    
    def close_connections(self):
        """Close all connections"""
        self.running = False
        
        for port, sock in self.sockets.items():
            try:
                sock.close()
                logger.info(f"🔌 Closed connection to port {port}")
            except Exception as e:
                logger.error(f"❌ Error closing port {port}: {e}")

def main():
    """Main function"""
    print("🛰️ MATLAB Bridge - Direct Port Sender")
    print("=" * 50)
    
    # Define device ports as per the configuration
    ars_ports = list(range(50038, 50050))      # 50038-50049 (12 ports)
    mag_ports = list(range(50050, 50053))      # 50050-50052 (3 ports)
    rw_ports = list(range(50053, 50057))      # 50053-50056 (4 ports)
    
    print(f"ARS ports: {ars_ports}")
    print(f"Magnetometer ports: {mag_ports}")
    print(f"Reaction Wheel ports: {rw_ports}")
    print(f"Total ports: {len(ars_ports) + len(mag_ports) + len(rw_ports)}")
    
    # Create bridge sender
    bridge = MATLABBridgeSender(ars_ports, mag_ports, rw_ports)
    
    try:
        # Run simulation for 60 seconds
        bridge.run_simulation(duration=60.0)
        
    except Exception as e:
        logger.error(f"❌ Bridge failed: {e}")
        
    finally:
        # Clean up
        bridge.close_connections()
        logger.info("🧹 Cleanup completed")

if __name__ == "__main__":
    main()
