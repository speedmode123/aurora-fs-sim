#!/usr/bin/env python3
"""
Reaction Wheel Status Manager for Device Simulator

Manages Reaction Wheel device status cycling with configurable scenarios.
Provides normal, warning, and error status configurations.
"""

import time
import random
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class RWAStatusScenario(Enum):
    """Reaction Wheel status scenarios"""
    NORMAL = "normal"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FAULT = "fault"

@dataclass
class RWAStatusConfig:
    """Reaction Wheel status configuration for a scenario"""
    mode: int = 1  # 0=STANDBY, 1=OPERATE
    status: int = 0x00  # NORMAL
    telemetry_type: int = 0x15  # HEALTH_STATUS
    temperature: float = 25.0  # °C
    bus_voltage: float = 28.0  # V
    motor_current: float = 0.5  # A
    wheel_speed: float = 1000.0  # RPM
    power_consumption: float = 14.0  # W
    motor_fault: bool = False
    temperature_fault: bool = False
    voltage_fault: bool = False
    communication_fault: bool = False

class RWAStatusManager:
    """Manages Reaction Wheel device status cycling"""
    
    def __init__(self, enabled: bool = False, cycle_interval: float = 10.0, 
                 scenarios: List[str] = None):
        self.enabled = enabled
        self.cycle_interval = cycle_interval
        self.scenarios = scenarios or ["normal"]
        self.current_scenario_index = 0
        self.last_cycle_time = time.time()
        
        # Define status configurations for each scenario
        self.status_configs = {
            RWAStatusScenario.NORMAL: RWAStatusConfig(
                mode=1,  # OPERATE
                status=0x00,  # NORMAL
                telemetry_type=0x15,  # HEALTH_STATUS
                temperature=25.0,
                bus_voltage=28.0,
                motor_current=0.5,
                wheel_speed=1000.0,
                power_consumption=14.0,
                motor_fault=False,
                temperature_fault=False,
                voltage_fault=False,
                communication_fault=False
            ),
            RWAStatusScenario.WARNING: RWAStatusConfig(
                mode=1,  # OPERATE
                status=0x01,  # WARNING
                telemetry_type=0x15,  # HEALTH_STATUS
                temperature=35.0,  # Higher temperature
                bus_voltage=27.5,  # Slightly low voltage
                motor_current=0.6,  # Higher current
                wheel_speed=1200.0,  # Higher speed
                power_consumption=16.8,  # Higher power
                motor_fault=False,
                temperature_fault=False,
                voltage_fault=False,
                communication_fault=False
            ),
            RWAStatusScenario.ERROR: RWAStatusConfig(
                mode=1,  # OPERATE
                status=0x02,  # ERROR
                telemetry_type=0x15,  # HEALTH_STATUS
                temperature=45.0,  # High temperature
                bus_voltage=26.0,  # Low voltage
                motor_current=0.8,  # High current
                wheel_speed=1500.0,  # High speed
                power_consumption=20.8,  # High power
                motor_fault=True,  # Motor fault
                temperature_fault=True,  # Temperature fault
                voltage_fault=False,
                communication_fault=False
            ),
            RWAStatusScenario.CRITICAL: RWAStatusConfig(
                mode=0,  # STANDBY (shutdown)
                status=0x03,  # CRITICAL
                telemetry_type=0x15,  # HEALTH_STATUS
                temperature=55.0,  # Critical temperature
                bus_voltage=24.0,  # Very low voltage
                motor_current=0.0,  # Motor off
                wheel_speed=0.0,  # Wheel stopped
                power_consumption=2.0,  # Minimal power
                motor_fault=True,
                temperature_fault=True,
                voltage_fault=True,  # Voltage fault
                communication_fault=False
            ),
            RWAStatusScenario.FAULT: RWAStatusConfig(
                mode=0,  # STANDBY
                status=0x04,  # FAULT
                telemetry_type=0x15,  # HEALTH_STATUS
                temperature=60.0,  # Fault temperature
                bus_voltage=22.0,  # Fault voltage
                motor_current=0.0,  # Motor off
                wheel_speed=0.0,  # Wheel stopped
                power_consumption=1.0,  # Minimal power
                motor_fault=True,
                temperature_fault=True,
                voltage_fault=True,
                communication_fault=True  # Communication fault
            )
        }
        
        logger.info(f"RWA Status Manager initialized: enabled={enabled}, "
                   f"cycle_interval={cycle_interval}s, scenarios={scenarios}")
    
    def get_current_status_config(self) -> RWAStatusConfig:
        """Get current status configuration"""
        if not self.enabled or not self.scenarios:
            return self.status_configs[RWAStatusScenario.NORMAL]
        
        # Check if it's time to cycle to next scenario
        current_time = time.time()
        if current_time - self.last_cycle_time >= self.cycle_interval:
            self.current_scenario_index = (self.current_scenario_index + 1) % len(self.scenarios)
            self.last_cycle_time = current_time
            
            current_scenario = self.scenarios[self.current_scenario_index]
            logger.debug(f"RWA status cycling to: {current_scenario}")
        
        # Get current scenario
        current_scenario = self.scenarios[self.current_scenario_index]
        try:
            scenario_enum = RWAStatusScenario(current_scenario)
            return self.status_configs[scenario_enum]
        except ValueError:
            logger.warning(f"Unknown RWA scenario: {current_scenario}, using NORMAL")
            return self.status_configs[RWAStatusScenario.NORMAL]
    
    def get_status_parameters(self) -> Dict[str, any]:
        """Get current status parameters"""
        config = self.get_current_status_config()
        
        return {
            'mode': config.mode,
            'status': config.status,
            'telemetry_type': config.telemetry_type,
            'temperature': config.temperature,
            'bus_voltage': config.bus_voltage,
            'motor_current': config.motor_current,
            'wheel_speed': config.wheel_speed,
            'power_consumption': config.power_consumption,
            'motor_fault': config.motor_fault,
            'temperature_fault': config.temperature_fault,
            'voltage_fault': config.voltage_fault,
            'communication_fault': config.communication_fault
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
            logger.info(f"RWA status forced to: {scenario}")
        else:
            logger.warning(f"Cannot force unknown scenario: {scenario}")
    
    def apply_status_effects(self, base_wheel_speed: float, base_current: float, 
                           base_temperature: float) -> Tuple[float, float, float]:
        """Apply status effects to base parameters"""
        config = self.get_current_status_config()
        
        # Apply mode effects
        if config.mode == 0:  # STANDBY
            wheel_speed = 0.0
            motor_current = 0.0
        else:  # OPERATE
            wheel_speed = base_wheel_speed
            motor_current = base_current
        
        # Apply fault effects
        if config.motor_fault:
            wheel_speed = 0.0
            motor_current = 0.0
        
        if config.temperature_fault:
            # Temperature affects motor performance
            temp_factor = max(0.0, 1.0 - (config.temperature - 25.0) / 30.0)
            wheel_speed *= temp_factor
            motor_current *= temp_factor
        
        if config.voltage_fault:
            # Low voltage affects performance
            voltage_factor = max(0.0, config.bus_voltage / 28.0)
            wheel_speed *= voltage_factor
            motor_current *= voltage_factor
        
        # Apply temperature from config
        temperature = config.temperature
        
        return (wheel_speed, motor_current, temperature)

def main():
    """Test RWA status manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RWA Status Manager Test')
    parser.add_argument('--enabled', action='store_true', help='Enable status cycling')
    parser.add_argument('--interval', type=float, default=5.0, help='Cycle interval in seconds')
    parser.add_argument('--scenarios', nargs='+', default=['normal', 'warning', 'error'], 
                       help='Status scenarios')
    parser.add_argument('--duration', type=float, default=30.0, help='Test duration')
    
    args = parser.parse_args()
    
    # Create status manager
    status_manager = RWAStatusManager(
        enabled=args.enabled,
        cycle_interval=args.interval,
        scenarios=args.scenarios
    )
    
    logger.info(f"Testing RWA Status Manager for {args.duration} seconds")
    
    start_time = time.time()
    while time.time() - start_time < args.duration:
        params = status_manager.get_status_parameters()
        scenario = status_manager.get_current_scenario()
        
        logger.info(f"Scenario: {scenario}, Mode: {params['mode']}, "
                   f"Status: 0x{params['status']:02X}, "
                   f"Speed: {params['wheel_speed']:.0f} RPM, "
                   f"Current: {params['motor_current']:.2f} A, "
                   f"Temp: {params['temperature']:.1f}°C")
        
        # Test status effects
        speed, current, temp = status_manager.apply_status_effects(1000.0, 0.5, 25.0)
        logger.debug(f"Status effects applied: Speed={speed:.0f}, Current={current:.2f}, Temp={temp:.1f}")
        
        time.sleep(1.0)
    
    logger.info("RWA Status Manager test complete")

if __name__ == '__main__':
    main()
