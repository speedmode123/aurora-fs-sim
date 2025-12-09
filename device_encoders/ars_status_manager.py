#!/usr/bin/env python3
"""
ARS Status Manager for Device Simulator

Manages ARS device status cycling with configurable scenarios.
Provides normal, warning, and error status configurations.
"""

import time
import random
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ARSStatusScenario(Enum):
    """ARS status scenarios"""
    NORMAL = "normal"
    WARNING = "warning"
    ERROR = "error"
    FAULT = "fault"

@dataclass
class ARSStatusConfig:
    """ARS status configuration for a scenario"""
    # Status Word 1 parameters
    bit_mode: int = 1  # 0=Power-up BIT, 1=Continuous BIT, 2=Initiated BIT
    rate_sensor_failed: bool = False
    gyro_failed: bool = False
    agc_voltage_failed: bool = False
    
    # Status Word 2 parameters
    gyro_temperature_a: int = 25  # Temperature in °C
    motor_bias_voltage_failed: bool = False
    start_data_flag: bool = False
    processor_failed: bool = False
    memory_failed: bool = False
    
    # Status Word 3 parameters
    gyro_a_start_run: bool = True
    gyro_b_start_run: bool = True
    gyro_c_start_run: bool = True
    gyro_a_fdc: bool = False
    gyro_b_fdc: bool = False
    gyro_c_fdc: bool = False
    fdc_failed: bool = False
    rs_ok: bool = True

class ARSStatusManager:
    """Manages ARS device status cycling"""
    
    def __init__(self, enabled: bool = False, cycle_interval: float = 10.0, 
                 scenarios: List[str] = None):
        self.enabled = enabled
        self.cycle_interval = cycle_interval
        self.scenarios = scenarios or ["normal"]
        self.current_scenario_index = 0
        self.last_cycle_time = time.time()
        
        # Define status configurations for each scenario
        self.status_configs = {
            ARSStatusScenario.NORMAL: ARSStatusConfig(
                bit_mode=1,
                rate_sensor_failed=False,
                gyro_failed=False,
                agc_voltage_failed=False,
                gyro_temperature_a=25,
                motor_bias_voltage_failed=False,
                start_data_flag=False,
                processor_failed=False,
                memory_failed=False,
                gyro_a_start_run=True,
                gyro_b_start_run=True,
                gyro_c_start_run=True,
                gyro_a_fdc=False,
                gyro_b_fdc=False,
                gyro_c_fdc=False,
                fdc_failed=False,
                rs_ok=True
            ),
            ARSStatusScenario.WARNING: ARSStatusConfig(
                bit_mode=1,
                rate_sensor_failed=False,
                gyro_failed=False,
                agc_voltage_failed=True,  # Warning: AGC voltage issue
                gyro_temperature_a=35,    # Warning: Higher temperature
                motor_bias_voltage_failed=False,
                start_data_flag=False,
                processor_failed=False,
                memory_failed=False,
                gyro_a_start_run=True,
                gyro_b_start_run=True,
                gyro_c_start_run=True,
                gyro_a_fdc=False,
                gyro_b_fdc=False,
                gyro_c_fdc=False,
                fdc_failed=False,
                rs_ok=True
            ),
            ARSStatusScenario.ERROR: ARSStatusConfig(
                bit_mode=1,
                rate_sensor_failed=True,  # Error: Rate sensor failed
                gyro_failed=False,
                agc_voltage_failed=True,
                gyro_temperature_a=45,    # Error: High temperature
                motor_bias_voltage_failed=True,  # Error: Motor bias voltage
                start_data_flag=False,
                processor_failed=False,
                memory_failed=False,
                gyro_a_start_run=True,
                gyro_b_start_run=True,
                gyro_c_start_run=True,
                gyro_a_fdc=False,
                gyro_b_fdc=False,
                gyro_c_fdc=False,
                fdc_failed=False,
                rs_ok=False  # Error: RS not OK
            ),
            ARSStatusScenario.FAULT: ARSStatusConfig(
                bit_mode=2,  # Fault: Initiated BIT mode
                rate_sensor_failed=True,
                gyro_failed=True,  # Fault: Gyro failed
                agc_voltage_failed=True,
                gyro_temperature_a=55,    # Fault: Critical temperature
                motor_bias_voltage_failed=True,
                start_data_flag=True,     # Fault: Start data flag
                processor_failed=True,    # Fault: Processor failed
                memory_failed=True,       # Fault: Memory failed
                gyro_a_start_run=False,   # Fault: Gyro A not running
                gyro_b_start_run=False,   # Fault: Gyro B not running
                gyro_c_start_run=False,   # Fault: Gyro C not running
                gyro_a_fdc=True,          # Fault: Gyro A FDC
                gyro_b_fdc=True,          # Fault: Gyro B FDC
                gyro_c_fdc=True,          # Fault: Gyro C FDC
                fdc_failed=True,          # Fault: FDC failed
                rs_ok=False
            )
        }
        
        logger.info(f"ARS Status Manager initialized: enabled={enabled}, "
                   f"cycle_interval={cycle_interval}s, scenarios={scenarios}")
    
    def get_current_status_config(self) -> ARSStatusConfig:
        """Get current status configuration"""
        if not self.enabled or not self.scenarios:
            return self.status_configs[ARSStatusScenario.NORMAL]
        
        # Check if it's time to cycle to next scenario
        current_time = time.time()
        if current_time - self.last_cycle_time >= self.cycle_interval:
            self.current_scenario_index = (self.current_scenario_index + 1) % len(self.scenarios)
            self.last_cycle_time = current_time
            
            current_scenario = self.scenarios[self.current_scenario_index]
            logger.debug(f"ARS status cycling to: {current_scenario}")
        
        # Get current scenario
        current_scenario = self.scenarios[self.current_scenario_index]
        try:
            scenario_enum = ARSStatusScenario(current_scenario)
            return self.status_configs[scenario_enum]
        except ValueError:
            logger.warning(f"Unknown ARS scenario: {current_scenario}, using NORMAL")
            return self.status_configs[ARSStatusScenario.NORMAL]
    
    def get_status_words(self) -> Tuple[int, int, int]:
        """Get current status words as tuple (word1, word2, word3)"""
        config = self.get_current_status_config()
        
        # Build Status Word 1
        word1 = 0
        word1 |= (0 & 0x03)  # Counter (always 0 for now)
        word1 |= ((config.bit_mode & 0x03) << 2)
        if config.rate_sensor_failed:
            word1 |= (1 << 4)
        if config.gyro_failed:
            word1 |= (1 << 5)
        if config.agc_voltage_failed:
            word1 |= (1 << 7)
        
        # Build Status Word 2
        word2 = 0
        word2 |= (config.gyro_temperature_a & 0xFF)
        if config.motor_bias_voltage_failed:
            word2 |= (1 << 8)
        if config.start_data_flag:
            word2 |= (1 << 9)
        if config.processor_failed:
            word2 |= (1 << 10)
        if config.memory_failed:
            word2 |= (1 << 11)
        
        # Build Status Word 3
        word3 = 0
        if config.gyro_a_start_run:
            word3 |= (1 << 8)
        if config.gyro_b_start_run:
            word3 |= (1 << 9)
        if config.gyro_c_start_run:
            word3 |= (1 << 10)
        if config.gyro_a_fdc:
            word3 |= (1 << 11)
        if config.gyro_b_fdc:
            word3 |= (1 << 12)
        if config.gyro_c_fdc:
            word3 |= (1 << 13)
        if config.fdc_failed:
            word3 |= (1 << 14)
        if config.rs_ok:
            word3 |= (1 << 15)
        
        return (word1 & 0xFFFF, word2 & 0xFFFF, word3 & 0xFFFF)
    
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
            logger.info(f"ARS status forced to: {scenario}")
        else:
            logger.warning(f"Cannot force unknown scenario: {scenario}")

def main():
    """Test ARS status manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ARS Status Manager Test')
    parser.add_argument('--enabled', action='store_true', help='Enable status cycling')
    parser.add_argument('--interval', type=float, default=5.0, help='Cycle interval in seconds')
    parser.add_argument('--scenarios', nargs='+', default=['normal', 'warning', 'error'], 
                       help='Status scenarios')
    parser.add_argument('--duration', type=float, default=30.0, help='Test duration')
    
    args = parser.parse_args()
    
    # Create status manager
    status_manager = ARSStatusManager(
        enabled=args.enabled,
        cycle_interval=args.interval,
        scenarios=args.scenarios
    )
    
    logger.info(f"Testing ARS Status Manager for {args.duration} seconds")
    
    start_time = time.time()
    while time.time() - start_time < args.duration:
        word1, word2, word3 = status_manager.get_status_words()
        scenario = status_manager.get_current_scenario()
        
        logger.info(f"Scenario: {scenario}, Status Words: 0x{word1:04X} 0x{word2:04X} 0x{word3:04X}")
        
        time.sleep(1.0)
    
    logger.info("ARS Status Manager test complete")

if __name__ == '__main__':
    main()
