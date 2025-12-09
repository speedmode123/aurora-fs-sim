#!/usr/bin/env python3
"""
Performance Monitor for Device Simulator

Monitors and optimizes performance of the device simulator.
Tracks latency, throughput, and resource usage.
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import statistics

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics for a component"""
    component_name: str
    total_operations: int = 0
    total_time: float = 0.0
    min_latency: float = float('inf')
    max_latency: float = 0.0
    recent_latencies: deque = field(default_factory=lambda: deque(maxlen=100))
    throughput_samples: deque = field(default_factory=lambda: deque(maxlen=60))  # 1 minute at 1Hz
    
    def add_sample(self, latency: float):
        """Add a latency sample"""
        self.total_operations += 1
        self.total_time += latency
        self.min_latency = min(self.min_latency, latency)
        self.max_latency = max(self.max_latency, latency)
        self.recent_latencies.append(latency)
    
    def get_average_latency(self) -> float:
        """Get average latency"""
        return self.total_time / self.total_operations if self.total_operations > 0 else 0.0
    
    def get_recent_average_latency(self) -> float:
        """Get average latency of recent samples"""
        return statistics.mean(self.recent_latencies) if self.recent_latencies else 0.0
    
    def get_latency_percentile(self, percentile: float) -> float:
        """Get latency percentile"""
        if not self.recent_latencies:
            return 0.0
        sorted_latencies = sorted(self.recent_latencies)
        index = int(len(sorted_latencies) * percentile / 100)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]

@dataclass
class SystemPerformanceMetrics:
    """System-wide performance metrics"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    network_latency: float = 0.0
    packet_loss_rate: float = 0.0
    total_packets_processed: int = 0
    total_bytes_processed: int = 0
    start_time: float = field(default_factory=time.time)

class PerformanceMonitor:
    """Monitors and optimizes system performance"""
    
    def __init__(self):
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.system_metrics = SystemPerformanceMetrics()
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.optimization_enabled = True
        
        # Performance thresholds
        self.latency_threshold_ms = 10.0  # 10ms threshold
        self.throughput_threshold = 1000  # packets/second
        self.cpu_threshold = 80.0  # 80% CPU usage
        
        logger.info("Performance Monitor initialized")
    
    def start_monitoring(self):
        """Start performance monitoring"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                self._update_system_metrics()
                self._check_performance_thresholds()
                self._apply_optimizations()
                time.sleep(1.0)  # Monitor every second
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                time.sleep(1.0)
    
    def _update_system_metrics(self):
        """Update system-wide metrics"""
        try:
            import psutil
            self.system_metrics.cpu_usage = psutil.cpu_percent()
            self.system_metrics.memory_usage = psutil.virtual_memory().percent
        except ImportError:
            # psutil not available, skip system metrics
            pass
    
    def _check_performance_thresholds(self):
        """Check if performance thresholds are exceeded"""
        for component_name, metrics in self.metrics.items():
            recent_avg = metrics.get_recent_average_latency()
            if recent_avg > self.latency_threshold_ms / 1000.0:  # Convert to seconds
                logger.warning(f"High latency detected in {component_name}: {recent_avg*1000:.2f}ms")
            
            if self.system_metrics.cpu_usage > self.cpu_threshold:
                logger.warning(f"High CPU usage detected: {self.system_metrics.cpu_usage:.1f}%")
    
    def _apply_optimizations(self):
        """Apply performance optimizations"""
        if not self.optimization_enabled:
            return
        
        # Optimize based on current performance
        for component_name, metrics in self.metrics.items():
            recent_avg = metrics.get_recent_average_latency()
            
            if recent_avg > self.latency_threshold_ms / 1000.0:
                self._optimize_component(component_name, metrics)
    
    def _optimize_component(self, component_name: str, metrics: PerformanceMetrics):
        """Apply optimizations to a specific component"""
        logger.info(f"Applying optimizations to {component_name}")
        
        # Component-specific optimizations
        if "encoder" in component_name:
            self._optimize_encoder(component_name)
        elif "transmitter" in component_name:
            self._optimize_transmitter(component_name)
        elif "receiver" in component_name:
            self._optimize_receiver(component_name)
    
    def _optimize_encoder(self, component_name: str):
        """Optimize encoder performance"""
        logger.debug(f"Optimizing encoder {component_name}")
        # Could implement caching, pre-computation, etc.
    
    def _optimize_transmitter(self, component_name: str):
        """Optimize transmitter performance"""
        logger.debug(f"Optimizing transmitter {component_name}")
        # Could implement batching, compression, etc.
    
    def _optimize_receiver(self, component_name: str):
        """Optimize receiver performance"""
        logger.debug(f"Optimizing receiver {component_name}")
        # Could implement buffering, async processing, etc.
    
    def measure_latency(self, component_name: str, operation_name: str = ""):
        """Context manager for measuring latency"""
        return LatencyTimer(self, component_name, operation_name)
    
    def get_component_metrics(self, component_name: str) -> PerformanceMetrics:
        """Get metrics for a specific component"""
        if component_name not in self.metrics:
            self.metrics[component_name] = PerformanceMetrics(component_name)
        return self.metrics[component_name]
    
    def get_performance_summary(self) -> Dict[str, any]:
        """Get comprehensive performance summary"""
        summary = {
            "system_metrics": {
                "cpu_usage": self.system_metrics.cpu_usage,
                "memory_usage": self.system_metrics.memory_usage,
                "uptime": time.time() - self.system_metrics.start_time,
                "total_packets": self.system_metrics.total_packets_processed,
                "total_bytes": self.system_metrics.total_bytes_processed
            },
            "component_metrics": {}
        }
        
        for component_name, metrics in self.metrics.items():
            summary["component_metrics"][component_name] = {
                "total_operations": metrics.total_operations,
                "average_latency_ms": metrics.get_average_latency() * 1000,
                "recent_average_latency_ms": metrics.get_recent_average_latency() * 1000,
                "min_latency_ms": metrics.min_latency * 1000 if metrics.min_latency != float('inf') else 0,
                "max_latency_ms": metrics.max_latency * 1000,
                "p95_latency_ms": metrics.get_latency_percentile(95) * 1000,
                "p99_latency_ms": metrics.get_latency_percentile(99) * 1000
            }
        
        return summary

class LatencyTimer:
    """Context manager for measuring latency"""
    
    def __init__(self, monitor: PerformanceMonitor, component_name: str, operation_name: str = ""):
        self.monitor = monitor
        self.component_name = component_name
        self.operation_name = operation_name
        self.start_time = 0.0
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        latency = time.time() - self.start_time
        metrics = self.monitor.get_component_metrics(self.component_name)
        metrics.add_sample(latency)
        
        if exc_type is not None:
            logger.debug(f"Operation {self.operation_name} in {self.component_name} failed after {latency*1000:.2f}ms")

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def measure_performance(component_name: str, operation_name: str = ""):
    """Convenience function for measuring performance"""
    return performance_monitor.measure_latency(component_name, operation_name)

def main():
    """Test performance monitor"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Performance Monitor Test')
    parser.add_argument('--test-duration', type=float, default=10.0, help='Test duration')
    parser.add_argument('--enable-monitoring', action='store_true', help='Enable monitoring')
    
    args = parser.parse_args()
    
    if args.enable_monitoring:
        performance_monitor.start_monitoring()
    
    logger.info(f"Testing performance monitor for {args.test_duration} seconds")
    
    start_time = time.time()
    while time.time() - start_time < args.test_duration:
        # Simulate some operations
        with measure_performance("test_encoder", "encode_data"):
            time.sleep(0.001)  # Simulate 1ms operation
        
        with measure_performance("test_transmitter", "send_data"):
            time.sleep(0.002)  # Simulate 2ms operation
        
        time.sleep(0.1)  # 100ms between operations
    
    # Show performance summary
    summary = performance_monitor.get_performance_summary()
    logger.info(f"Performance Summary: {summary}")
    
    if args.enable_monitoring:
        performance_monitor.stop_monitoring()
    
    logger.info("Performance Monitor test complete")

if __name__ == '__main__':
    main()
