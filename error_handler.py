#!/usr/bin/env python3
"""
Error Handler for Device Simulator

Provides comprehensive error handling and graceful degradation for the simulator.
Handles various error scenarios and provides recovery mechanisms.
"""

import time
import logging
import traceback
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"          # Non-critical, continue operation
    MEDIUM = "medium"    # Important, log warning, may affect performance
    HIGH = "high"        # Critical, log error, may stop device
    CRITICAL = "critical" # Fatal, stop entire system

class ErrorType(Enum):
    """Error types"""
    CONNECTION = "connection"
    DATA_PROCESSING = "data_processing"
    ENCODING = "encoding"
    TRANSMISSION = "transmission"
    CONFIGURATION = "configuration"
    HARDWARE = "hardware"
    NETWORK = "network"
    SYSTEM = "system"

@dataclass
class ErrorContext:
    """Context information for an error"""
    device_name: str = ""
    component: str = ""
    operation: str = ""
    error_type: ErrorType = ErrorType.SYSTEM
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    retry_count: int = 0
    max_retries: int = 3
    last_error_time: float = 0.0
    error_count: int = 0

class ErrorHandler:
    """Comprehensive error handler for the device simulator"""
    
    def __init__(self):
        self.error_contexts: Dict[str, ErrorContext] = {}
        self.error_callbacks: Dict[ErrorType, List[Callable]] = {}
        self.recovery_strategies: Dict[ErrorType, Callable] = {}
        self.error_stats: Dict[str, Dict[str, int]] = {}
        
        # Initialize error statistics
        for error_type in ErrorType:
            self.error_stats[error_type.value] = {
                "total_errors": 0,
                "recovered_errors": 0,
                "failed_recoveries": 0
            }
        
        logger.info("Error Handler initialized")
    
    def register_error_callback(self, error_type: ErrorType, callback: Callable):
        """Register a callback for specific error types"""
        if error_type not in self.error_callbacks:
            self.error_callbacks[error_type] = []
        self.error_callbacks[error_type].append(callback)
        logger.debug(f"Registered error callback for {error_type.value}")
    
    def register_recovery_strategy(self, error_type: ErrorType, strategy: Callable):
        """Register a recovery strategy for specific error types"""
        self.recovery_strategies[error_type] = strategy
        logger.debug(f"Registered recovery strategy for {error_type.value}")
    
    def handle_error(self, error: Exception, context: ErrorContext) -> bool:
        """
        Handle an error with context information
        
        Returns:
            bool: True if error was handled successfully, False otherwise
        """
        # Update error context
        context.error_count += 1
        context.last_error_time = time.time()
        
        # Update statistics
        self.error_stats[context.error_type.value]["total_errors"] += 1
        
        # Log error based on severity
        self._log_error(error, context)
        
        # Execute error callbacks
        self._execute_callbacks(context.error_type, error, context)
        
        # Attempt recovery
        recovery_success = self._attempt_recovery(error, context)
        
        # Update statistics
        if recovery_success:
            self.error_stats[context.error_type.value]["recovered_errors"] += 1
        else:
            self.error_stats[context.error_type.value]["failed_recoveries"] += 1
        
        return recovery_success
    
    def _log_error(self, error: Exception, context: ErrorContext):
        """Log error with appropriate level based on severity"""
        error_msg = f"Error in {context.component} for {context.device_name}: {str(error)}"
        
        if context.severity == ErrorSeverity.LOW:
            logger.debug(error_msg)
        elif context.severity == ErrorSeverity.MEDIUM:
            logger.warning(error_msg)
        elif context.severity == ErrorSeverity.HIGH:
            logger.error(error_msg)
        elif context.severity == ErrorSeverity.CRITICAL:
            logger.critical(error_msg)
            logger.critical(f"Stack trace: {traceback.format_exc()}")
    
    def _execute_callbacks(self, error_type: ErrorType, error: Exception, context: ErrorContext):
        """Execute registered callbacks for the error type"""
        if error_type in self.error_callbacks:
            for callback in self.error_callbacks[error_type]:
                try:
                    callback(error, context)
                except Exception as callback_error:
                    logger.error(f"Error in callback: {callback_error}")
    
    def _attempt_recovery(self, error: Exception, context: ErrorContext) -> bool:
        """Attempt to recover from the error"""
        if context.error_type in self.recovery_strategies:
            try:
                recovery_strategy = self.recovery_strategies[context.error_type]
                return recovery_strategy(error, context)
            except Exception as recovery_error:
                logger.error(f"Recovery strategy failed: {recovery_error}")
                return False
        
        # Default recovery strategies
        return self._default_recovery(error, context)
    
    def _default_recovery(self, error: Exception, context: ErrorContext) -> bool:
        """Default recovery strategies based on error type"""
        if context.error_type == ErrorType.CONNECTION:
            return self._recover_connection_error(error, context)
        elif context.error_type == ErrorType.DATA_PROCESSING:
            return self._recover_data_processing_error(error, context)
        elif context.error_type == ErrorType.ENCODING:
            return self._recover_encoding_error(error, context)
        elif context.error_type == ErrorType.TRANSMISSION:
            return self._recover_transmission_error(error, context)
        else:
            return self._recover_generic_error(error, context)
    
    def _recover_connection_error(self, error: Exception, context: ErrorContext) -> bool:
        """Recover from connection errors"""
        if context.retry_count < context.max_retries:
            context.retry_count += 1
            logger.info(f"Retrying connection for {context.device_name} (attempt {context.retry_count})")
            time.sleep(min(2 ** context.retry_count, 30))  # Exponential backoff
            return True
        else:
            logger.error(f"Max retries exceeded for {context.device_name} connection")
            return False
    
    def _recover_data_processing_error(self, error: Exception, context: ErrorContext) -> bool:
        """Recover from data processing errors"""
        logger.warning(f"Skipping malformed data for {context.device_name}")
        return True  # Skip bad data and continue
    
    def _recover_encoding_error(self, error: Exception, context: ErrorContext) -> bool:
        """Recover from encoding errors"""
        logger.warning(f"Using default encoding for {context.device_name}")
        return True  # Use default values
    
    def _recover_transmission_error(self, error: Exception, context: ErrorContext) -> bool:
        """Recover from transmission errors"""
        logger.warning(f"Transmission failed for {context.device_name}, continuing in simulation mode")
        return True  # Continue in simulation mode
    
    def _recover_generic_error(self, error: Exception, context: ErrorContext) -> bool:
        """Generic error recovery"""
        if context.severity == ErrorSeverity.CRITICAL:
            return False
        else:
            logger.warning(f"Generic recovery for {context.device_name}")
            return True
    
    def get_error_context(self, device_name: str, component: str) -> ErrorContext:
        """Get or create error context for a device/component"""
        key = f"{device_name}:{component}"
        if key not in self.error_contexts:
            self.error_contexts[key] = ErrorContext(
                device_name=device_name,
                component=component
            )
        return self.error_contexts[key]
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        total_errors = sum(stats["total_errors"] for stats in self.error_stats.values())
        total_recovered = sum(stats["recovered_errors"] for stats in self.error_stats.values())
        total_failed = sum(stats["failed_recoveries"] for stats in self.error_stats.values())
        
        recovery_rate = (total_recovered / total_errors * 100) if total_errors > 0 else 0
        
        return {
            "total_errors": total_errors,
            "recovered_errors": total_recovered,
            "failed_recoveries": total_failed,
            "recovery_rate": recovery_rate,
            "error_types": self.error_stats,
            "active_contexts": len(self.error_contexts)
        }
    
    def reset_error_context(self, device_name: str, component: str):
        """Reset error context for a device/component"""
        key = f"{device_name}:{component}"
        if key in self.error_contexts:
            context = self.error_contexts[key]
            context.retry_count = 0
            context.error_count = 0
            logger.info(f"Reset error context for {device_name}:{component}")

# Global error handler instance
error_handler = ErrorHandler()

def handle_error(error: Exception, device_name: str, component: str, 
                operation: str = "", error_type: ErrorType = ErrorType.SYSTEM,
                severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> bool:
    """
    Convenience function to handle errors
    
    Returns:
        bool: True if error was handled successfully, False otherwise
    """
    context = error_handler.get_error_context(device_name, component)
    context.operation = operation
    context.error_type = error_type
    context.severity = severity
    
    return error_handler.handle_error(error, context)

def main():
    """Test error handler"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Error Handler Test')
    parser.add_argument('--test-errors', action='store_true', help='Test various error scenarios')
    parser.add_argument('--duration', type=float, default=10.0, help='Test duration')
    
    args = parser.parse_args()
    
    if args.test_errors:
        logger.info("Testing error handler scenarios")
        
        # Test connection error
        try:
            raise ConnectionError("USB port not found")
        except Exception as e:
            handle_error(e, "ars", "serial_transmitter", "connect", 
                        ErrorType.CONNECTION, ErrorSeverity.MEDIUM)
        
        # Test data processing error
        try:
            raise ValueError("Invalid data format")
        except Exception as e:
            handle_error(e, "magnetometer", "encoder", "process_data", 
                        ErrorType.DATA_PROCESSING, ErrorSeverity.LOW)
        
        # Test encoding error
        try:
            raise struct.error("Invalid struct format")
        except Exception as e:
            handle_error(e, "reaction_wheel", "encoder", "encode_packet", 
                        ErrorType.ENCODING, ErrorSeverity.HIGH)
        
        # Show statistics
        stats = error_handler.get_error_statistics()
        logger.info(f"Error Statistics: {stats}")
    
    logger.info("Error Handler test complete")

if __name__ == '__main__':
    main()
