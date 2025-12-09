import serial
import time
from dataclasses import dataclass


@dataclass
class USBPortConfig:
    """Configuration for USB port"""
    port: str
    baud_rate: int = 115200
    data_bits: int = 8
    stop_bits: int = 1
    parity: str = "N"
    timeout: float = 1.0
    
config = USBPortConfig(port="/dev/ttyUSB0")
    
monitor = serial.Serial(
                    port=config.port,
                    baudrate=config.baud_rate,
                    bytesize=config.data_bits,
                    stopbits=config.stop_bits,
                    parity=config.parity,
                    timeout=config.timeout
                )
                
while True:
    monitor.write(b'0')
    print("Writing something to /dev/ttyUSB0")
    time.sleep(1)
    
