#!/usr/bin/env python3
"""
Magnetometer Status Manager for Device Simulator

Manages Magnetometer device status cycling with configurable scenarios.
Provides normal, warning, and error status configurations.
"""

import time
import random
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class MagnetometerStatusScenario(Enum):
    """Magnetometer status scenarios"""
    NORMAL = "normal"
    WARNING = "warning"
    ERROR = "error"
    CALIBRATION_MODE = "calibration_mode"
    MEMORY_ERROR = "memory_error"
    COMMUNICATION_ERROR = "communication_error"

@dataclass
class MagnetometerStatusConfig:
    """Magnetometer status configuration for a scenario"""
    status: int = 0x00  # NORMAL
    message_type: int = 0x01  # MAGDATA
    temperature: float = 25.0  # °C
    calibration_active: bool = False
    memory_error: bool = False
    communication_error: bool = False
    data_quality: float = 1.0  # 0.0 to 1.0

class MagnetometerStatusManager:
    """Manages Magnetometer device status cycling"""
    
    def __init__(self, enabled: bool = False, cycle_interval: float = 10.0, 
                 scenarios: List[str] = None):
        self.enabled = enabled
        self.cycle_interval = cycle_interval
        self.scenarios = scenarios or ["normal"]
        self.current_scenario_index = 0
        self.last_cycle_time = time.time()
        
        # Define status configurations for each scenario
        self.status_configs = {
            MagnetometerStatusScenario.NORMAL: MagnetometerStatusConfig(
                status=0x00,  # NORMAL
                message_type=0x01,  # MAGDATA
                temperature=25.0,
                calibration_active=False,
                memory_error=False,
                communication_error=False,
                data_quality=1.0
            ),
            MagnetometerStatusScenario.WARNING: MagnetometerStatusConfig(
                status=0x01,  # WARNING
                message_type=0x01,  # MAGDATA
                temperature=35.0,  # Higher temperature
                calibration_active=False,
                memory_error=False,
                communication_error=False,
                data_quality=0.8  # Slightly reduced quality
            ),
            MagnetometerStatusScenario.ERROR: MagnetometerStatusConfig(
                status=0x02,  # ERROR
                message_type=0x01,  # MAGDATA
                temperature=45.0,  # High temperature
                calibration_active=False,
                memory_error=False,
                communication_error=True,  # Communication error
                data_quality=0.5  # Reduced quality
            ),
            MagnetometerStatusScenario.CALIBRATION_MODE: MagnetometerStatusConfig(
                status=0x04,  # CALIBRATION_MODE
                message_type=0x07,  # OPMODE
                temperature=25.0,
                calibration_active=True,
                memory_error=False,
                communication_error=False,
                data_quality=0.9  # Good quality during calibration
            ),
            MagnetometerStatusScenario.MEMORY_ERROR: MagnetometerStatusConfig(
                status=0x05,  # MEMORY_ERROR
                message_type=0x08,  # STATUS
                temperature=25.0,
                calibration_active=False,
                memory_error=True,
                communication_error=False,
                data_quality=0.3  # Poor quality due to memory issues
            ),
            MagnetometerStatusScenario.COMMUNICATION_ERROR: MagnetometerStatusConfig(
                status=0x06,  # COMMUNICATION_ERROR
                message_type=0x08,  # STATUS
                temperature=25.0,
                calibration_active=False,
                memory_error=False,
                communication_error=True,
                data_quality=0.1  # Very poor quality
            )
        }
        
        logger.info(f"Magnetometer Status Manager initialized: enabled={enabled}, "
                   f"cycle_interval={cycle_interval}s, scenarios={scenarios}")
    
    def get_current_status_config(self) -> MagnetometerStatusConfig:
        """Get current status configuration"""
        if not self.enabled or not self.scenarios:
            return self.status_configs[MagnetometerStatusScenario.NORMAL]
        
        # Check if it's time to cycle to next scenario
        current_time = time.time()
        if current_time - self.last_cycle_time >= self.cycle_interval:
            self.current_scenario_index = (self.current_scenario_index + 1) % len(self.scenarios)
            self.last_cycle_time = current_time
            
            current_scenario = self.scenarios[self.current_scenario_index]
            logger.debug(f"Magnetometer status cycling to: {current_scenario}")
        
        # Get current scenario
        current_scenario = self.scenarios[self.current_scenario_index]
        try:
            scenario_enum = MagnetometerStatusScenario(current_scenario)
            return self.status_configs[scenario_enum]
        except ValueError:
            logger.warning(f"Unknown Magnetometer scenario: {current_scenario}, using NORMAL")
            return self.status_configs[MagnetometerStatusScenario.NORMAL]
    
    def get_status_parameters(self) -> Dict[str, any]:
        """Get current status parameters"""
        config = self.get_current_status_config()
        
        return {
            'status': config.status,
            'message_type': config.message_type,
            'temperature': config.temperature,
            'calibration_active': config.calibration_active,
            'memory_error': config.memory_error,
            'communication_error': config.communication_error,
            'data_quality': config.data_quality
        }
    
    def get_current_scenario(self) -> str:
        """Get current scenario name"""
        if not self.enabled or not self.scenarios:
            return "normal"
        return self.scenarios[self.current_scenario_index]
    
    def force_scenario(self, scenario: str):
        """Force a specific scenario"""
        if scenario in self.scenarios:
            self.current_scenario_index = self.scenarios.index(scenario)
            self.last_cycle_time = time.time()
            logger.info(f"Magnetometer status forced to: {scenario}")
        else:
            logger.warning(f"Cannot force unknown scenario: {scenario}")
    
    def apply_data_quality(self, x_field: float, y_field: float, z_field: float) -> Tuple[float, float, float]:
        """Apply data quality factor to magnetic field measurements"""
        config = self.get_current_status_config()
        
        if config.data_quality < 1.0:
            # Add noise based on quality factor
            noise_factor = (1.0 - config.data_quality) * 0.1  # Up to 10% noise
            noise_x = random.uniform(-noise_factor, noise_factor) * abs(x_field)
            noise_y = random.uniform(-noise_factor, noise_factor) * abs(y_field)
            noise_z = random.uniform(-noise_factor, noise_factor) * abs(z_field)
            
            return (
                x_field + noise_x,
                y_field + noise_y,
                z_field + noise_z
            )
        
        return (x_field, y_field, z_field)

def main():
    """Test Magnetometer status manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Magnetometer Status Manager Test')
    parser.add_argument('--enabled', action='store_true', help='Enable status cycling')
    parser.add_argument('--interval', type=float, default=5.0, help='Cycle interval in seconds')
    parser.add_argument('--scenarios', nargs='+', default=['normal', 'warning', 'calibration_mode'], 
                       help='Status scenarios')
    parser.add_argument('--duration', type=float, default=30.0, help='Test duration')
    
    args = parser.parse_args()
    
    # Create status manager
    status_manager = MagnetometerStatusManager(
        enabled=args.enabled,
        cycle_interval=args.interval,
        scenarios=args.scenarios
    )
    
    logger.info(f"Testing Magnetometer Status Manager for {args.duration} seconds")
    
    start_time = time.time()
    while time.time() - start_time < args.duration:
        params = status_manager.get_status_parameters()
        scenario = status_manager.get_current_scenario()
        
        logger.info(f"Scenario: {scenario}, Status: 0x{params['status']:02X}, "
                   f"Message Type: 0x{params['message_type']:02X}, "
                   f"Temperature: {params['temperature']:.1f}°C, "
                   f"Quality: {params['data_quality']:.2f}")
        
        # Test data quality application
        x, y, z = status_manager.apply_data_quality(100.0, 200.0, 300.0)
        logger.debug(f"Data quality applied: X={x:.2f}, Y={y:.2f}, Z={z:.2f}")
        
        time.sleep(1.0)
    
    logger.info("Magnetometer Status Manager test complete")

if __name__ == '__main__':
    main()
