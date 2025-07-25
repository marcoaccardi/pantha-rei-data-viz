#!/usr/bin/env python3
"""
Performance monitoring utilities for backend-api system.
Tracks API response times, system resources, and operational metrics.
"""

import time
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
import logging
from pathlib import Path
import threading

class PerformanceMonitor:
    """Monitor and track system performance metrics."""
    
    def __init__(self, metrics_file: Optional[Path] = None, 
                 history_size: int = 1000):
        """
        Initialize performance monitor.
        
        Args:
            metrics_file: Optional file to persist metrics
            history_size: Number of historical data points to keep
        """
        self.logger = logging.getLogger(__name__)
        self.metrics_file = metrics_file
        self.history_size = history_size
        
        # Request tracking
        self.request_times = defaultdict(lambda: deque(maxlen=history_size))
        self.error_counts = defaultdict(int)
        self.success_counts = defaultdict(int)
        
        # System metrics
        self.system_metrics = deque(maxlen=history_size)
        
        # Start time for uptime calculation
        self.start_time = datetime.now()
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        self.logger.info("Performance monitor initialized")
    
    def track_request(self, api_name: str, endpoint: str, start_time: float, 
                     end_time: float, success: bool, error: Optional[str] = None):
        """
        Track API request performance.
        
        Args:
            api_name: Name of the API
            endpoint: API endpoint called
            start_time: Request start time (from time.time())
            end_time: Request end time (from time.time())
            success: Whether request was successful
            error: Error message if failed
        """
        with self.lock:
            response_time = end_time - start_time
            key = f"{api_name}:{endpoint}"
            
            # Track response time
            self.request_times[key].append({
                'timestamp': datetime.now().isoformat(),
                'response_time': response_time,
                'success': success
            })
            
            # Update counters
            if success:
                self.success_counts[key] += 1
            else:
                self.error_counts[key] += 1
                
                if error:
                    error_key = f"{key}:{error[:50]}"  # Truncate error message
                    self.error_counts[error_key] += 1
            
            # Log slow requests
            if response_time > 5.0:  # 5 seconds
                self.logger.warning(
                    f"Slow request detected: {key} took {response_time:.2f}s"
                )
    
    def record_system_metrics(self):
        """Record current system resource usage."""
        with self.lock:
            try:
                # Get system metrics
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Get process-specific metrics
                process = psutil.Process()
                process_info = process.as_dict(attrs=[
                    'cpu_percent', 'memory_percent', 'memory_info', 'num_threads'
                ])
                
                metrics = {
                    'timestamp': datetime.now().isoformat(),
                    'system': {
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory.percent,
                        'memory_available_mb': memory.available / 1024 / 1024,
                        'disk_percent': disk.percent,
                        'disk_free_gb': disk.free / 1024 / 1024 / 1024
                    },
                    'process': {
                        'cpu_percent': process_info['cpu_percent'],
                        'memory_percent': process_info['memory_percent'],
                        'memory_rss_mb': process_info['memory_info'].rss / 1024 / 1024,
                        'num_threads': process_info['num_threads']
                    }
                }
                
                self.system_metrics.append(metrics)
                
                # Check for resource warnings
                if cpu_percent > 80:
                    self.logger.warning(f"High CPU usage: {cpu_percent}%")
                if memory.percent > 85:
                    self.logger.warning(f"High memory usage: {memory.percent}%")
                    
            except Exception as e:
                self.logger.error(f"Error recording system metrics: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive performance statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        with self.lock:
            stats = {
                'timestamp': datetime.now().isoformat(),
                'uptime_hours': (datetime.now() - self.start_time).total_seconds() / 3600,
                'api_performance': {},
                'system_health': {},
                'error_summary': {}
            }
            
            # Calculate API performance stats
            for key, times in self.request_times.items():
                if times:
                    response_times = [t['response_time'] for t in times]
                    success_count = self.success_counts.get(key, 0)
                    error_count = self.error_counts.get(key, 0)
                    total_requests = success_count + error_count
                    
                    stats['api_performance'][key] = {
                        'total_requests': total_requests,
                        'success_count': success_count,
                        'error_count': error_count,
                        'success_rate': (success_count / total_requests * 100) if total_requests > 0 else 0,
                        'avg_response_time': sum(response_times) / len(response_times),
                        'min_response_time': min(response_times),
                        'max_response_time': max(response_times),
                        'p95_response_time': self._calculate_percentile(response_times, 95),
                        'p99_response_time': self._calculate_percentile(response_times, 99)
                    }
            
            # Get latest system metrics
            if self.system_metrics:
                latest_metrics = self.system_metrics[-1]
                stats['system_health'] = {
                    'current': latest_metrics,
                    'averages': self._calculate_system_averages()
                }
            
            # Error summary
            error_summary = {}
            for key, count in self.error_counts.items():
                if ':' in key and count > 0:
                    error_summary[key] = count
            stats['error_summary'] = error_summary
            
            return stats
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value from a list."""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _calculate_system_averages(self) -> Dict[str, float]:
        """Calculate average system metrics."""
        if not self.system_metrics:
            return {}
        
        # Get metrics from last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_metrics = [
            m for m in self.system_metrics 
            if datetime.fromisoformat(m['timestamp']) > one_hour_ago
        ]
        
        if not recent_metrics:
            return {}
        
        # Calculate averages
        avg_cpu = sum(m['system']['cpu_percent'] for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m['system']['memory_percent'] for m in recent_metrics) / len(recent_metrics)
        avg_process_cpu = sum(m['process']['cpu_percent'] for m in recent_metrics) / len(recent_metrics)
        avg_process_memory = sum(m['process']['memory_percent'] for m in recent_metrics) / len(recent_metrics)
        
        return {
            'avg_system_cpu_percent': round(avg_cpu, 2),
            'avg_system_memory_percent': round(avg_memory, 2),
            'avg_process_cpu_percent': round(avg_process_cpu, 2),
            'avg_process_memory_percent': round(avg_process_memory, 2)
        }
    
    def save_metrics(self):
        """Save current metrics to file."""
        if not self.metrics_file:
            return
        
        try:
            stats = self.get_performance_stats()
            
            # Ensure directory exists
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save as JSON
            with open(self.metrics_file, 'w') as f:
                json.dump(stats, f, indent=2)
            
            self.logger.debug(f"Metrics saved to {self.metrics_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving metrics: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get system health status with recommendations.
        
        Returns:
            Health status dictionary
        """
        stats = self.get_performance_stats()
        
        health = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'issues': [],
            'recommendations': []
        }
        
        # Check API performance
        for api_key, perf in stats['api_performance'].items():
            if perf['success_rate'] < 90:
                health['issues'].append(
                    f"Low success rate for {api_key}: {perf['success_rate']:.1f}%"
                )
                health['status'] = 'degraded'
            
            if perf['avg_response_time'] > 2.0:
                health['issues'].append(
                    f"High average response time for {api_key}: {perf['avg_response_time']:.2f}s"
                )
                health['recommendations'].append(
                    f"Consider caching more aggressively for {api_key}"
                )
        
        # Check system resources
        if stats['system_health']:
            current = stats['system_health']['current']['system']
            
            if current['cpu_percent'] > 80:
                health['issues'].append(f"High CPU usage: {current['cpu_percent']}%")
                health['status'] = 'warning'
            
            if current['memory_percent'] > 85:
                health['issues'].append(f"High memory usage: {current['memory_percent']}%")
                health['status'] = 'warning'
                health['recommendations'].append("Consider increasing system memory")
            
            if current['disk_percent'] > 90:
                health['issues'].append(f"Low disk space: {current['disk_percent']}% used")
                health['status'] = 'critical'
                health['recommendations'].append("Clean up cache or increase disk space")
        
        # Check error rates
        total_errors = sum(stats['error_summary'].values())
        if total_errors > 100:
            health['issues'].append(f"High error count: {total_errors} errors")
            health['recommendations'].append("Review error logs and fix underlying issues")
        
        return health


class RequestTimer:
    """Context manager for timing requests."""
    
    def __init__(self, monitor: PerformanceMonitor, api_name: str, endpoint: str):
        self.monitor = monitor
        self.api_name = api_name
        self.endpoint = endpoint
        self.start_time = None
        self.success = True
        self.error = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        
        if exc_type is not None:
            self.success = False
            self.error = str(exc_val)
        
        self.monitor.track_request(
            self.api_name,
            self.endpoint,
            self.start_time,
            end_time,
            self.success,
            self.error
        )
        
        # Don't suppress exceptions
        return False


def main():
    """Test performance monitor."""
    import tempfile
    import random
    
    with tempfile.NamedTemporaryFile(suffix='.json') as temp_file:
        monitor = PerformanceMonitor(metrics_file=Path(temp_file.name))
        
        print("📊 PERFORMANCE MONITOR TEST")
        print("=" * 50)
        
        # Simulate API requests
        print("\n🔄 Simulating API requests...")
        
        for i in range(20):
            api = random.choice(['copernicus', 'pangaea', 'noaa'])
            endpoint = random.choice(['/subset', '/query', '/search'])
            
            # Use RequestTimer context manager
            try:
                with RequestTimer(monitor, api, endpoint) as timer:
                    # Simulate processing time
                    time.sleep(random.uniform(0.1, 0.5))
                    
                    # Simulate some failures
                    if random.random() < 0.1:
                        raise Exception("Simulated API error")
                        
            except Exception:
                pass  # Error is tracked by RequestTimer
        
        # Record system metrics
        print("\n💻 Recording system metrics...")
        for _ in range(5):
            monitor.record_system_metrics()
            time.sleep(0.2)
        
        # Get performance stats
        stats = monitor.get_performance_stats()
        print("\n📈 Performance Statistics:")
        print(f"  Uptime: {stats['uptime_hours']:.2f} hours")
        
        print("\n  API Performance:")
        for api_key, perf in stats['api_performance'].items():
            print(f"    {api_key}:")
            print(f"      Requests: {perf['total_requests']}")
            print(f"      Success rate: {perf['success_rate']:.1f}%")
            print(f"      Avg response: {perf['avg_response_time']:.3f}s")
        
        # Get health status
        health = monitor.get_health_status()
        print(f"\n🏥 Health Status: {health['status'].upper()}")
        
        if health['issues']:
            print("  Issues:")
            for issue in health['issues']:
                print(f"    ⚠️ {issue}")
        
        if health['recommendations']:
            print("  Recommendations:")
            for rec in health['recommendations']:
                print(f"    💡 {rec}")
        
        # Save metrics
        monitor.save_metrics()
        print(f"\n📄 Metrics saved to: {temp_file.name}")

if __name__ == "__main__":
    main()