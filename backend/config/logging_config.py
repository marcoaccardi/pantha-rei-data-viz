#!/usr/bin/env python3
"""
Production logging configuration for backend-api system.
Provides structured logging with rotation and multiple handlers.
"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

def setup_production_logging(
    log_level: str = None,
    log_dir: Path = None,
    enable_console: bool = True,
    enable_file: bool = True
) -> logging.Logger:
    """
    Configure logging for production deployment.
    
    Args:
        log_level: Logging level (INFO, DEBUG, WARNING, ERROR)
        log_dir: Directory for log files
        enable_console: Enable console output
        enable_file: Enable file logging
        
    Returns:
        Configured root logger
    """
    
    # Get configuration from environment or use defaults
    log_level = log_level or os.getenv('LOG_LEVEL', 'INFO')
    log_dir = log_dir or Path(os.getenv('LOG_DIR', 'logs'))
    
    # Create log directory
    log_dir.mkdir(exist_ok=True)
    
    # Configure formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(simple_formatter)
        console_handler.setLevel(logging.INFO)
        root_logger.addHandler(console_handler)
    
    if enable_file:
        # Main application log with rotation
        app_log_file = log_dir / 'backend_api.log'
        app_handler = logging.handlers.RotatingFileHandler(
            app_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        app_handler.setFormatter(detailed_formatter)
        app_handler.setLevel(logging.INFO)
        root_logger.addHandler(app_handler)
        
        # Error log file
        error_log_file = log_dir / 'errors.log'
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3
        )
        error_handler.setFormatter(detailed_formatter)
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)
        
        # API request log
        api_log_file = log_dir / 'api_requests.log'
        api_handler = logging.handlers.RotatingFileHandler(
            api_log_file,
            maxBytes=20 * 1024 * 1024,  # 20MB
            backupCount=7
        )
        api_handler.setFormatter(detailed_formatter)
        api_handler.setLevel(logging.INFO)
        
        # Create API logger
        api_logger = logging.getLogger('backend_api')
        api_logger.addHandler(api_handler)
        api_logger.propagate = False  # Don't propagate to root logger
    
    # Configure specific loggers
    configure_module_loggers()
    
    # Log startup message
    root_logger.info("=" * 60)
    root_logger.info(f"Backend-API Ocean Climate Data System - Started at {datetime.now()}")
    root_logger.info(f"Log Level: {log_level}")
    root_logger.info(f"Log Directory: {log_dir}")
    root_logger.info("=" * 60)
    
    return root_logger

def configure_module_loggers():
    """Configure logging levels for specific modules."""
    
    # Suppress verbose libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.INFO)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    
    # Configure API client loggers
    logging.getLogger('clients.copernicus_client_production').setLevel(logging.INFO)
    logging.getLogger('clients.pangaea_client').setLevel(logging.INFO)
    logging.getLogger('clients.noaa_cops_client').setLevel(logging.INFO)
    
    # Configure utility loggers
    logging.getLogger('utils.cache_manager').setLevel(logging.INFO)
    logging.getLogger('utils.coordinate_validator').setLevel(logging.INFO)
    logging.getLogger('utils.performance_monitor').setLevel(logging.INFO)

class APIRequestLogger:
    """Specialized logger for API requests with structured data."""
    
    def __init__(self, logger_name: str = 'backend_api.api_requests'):
        self.logger = logging.getLogger(logger_name)
    
    def log_request(self, api_name: str, endpoint: str, params: dict, 
                   response_time: float, status: str, error: Optional[str] = None):
        """Log API request with structured data."""
        log_data = {
            'api_name': api_name,
            'endpoint': endpoint,
            'params': params,
            'response_time_ms': response_time * 1000,
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
        
        if error:
            log_data['error'] = error
            self.logger.error(f"API Request Failed: {json.dumps(log_data)}")
        else:
            self.logger.info(f"API Request: {json.dumps(log_data)}")
    
    def log_websocket_message(self, client_id: str, message_type: str, 
                            direction: str, size_bytes: int):
        """Log WebSocket message."""
        log_data = {
            'client_id': client_id,
            'message_type': message_type,
            'direction': direction,  # 'incoming' or 'outgoing'
            'size_bytes': size_bytes,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"WebSocket Message: {json.dumps(log_data)}")

class PerformanceLogger:
    """Logger for performance metrics."""
    
    def __init__(self, logger_name: str = 'backend_api.performance'):
        self.logger = logging.getLogger(logger_name)
    
    def log_metric(self, metric_name: str, value: float, unit: str, 
                  tags: Optional[dict] = None):
        """Log performance metric."""
        log_data = {
            'metric': metric_name,
            'value': value,
            'unit': unit,
            'timestamp': datetime.now().isoformat()
        }
        
        if tags:
            log_data['tags'] = tags
        
        self.logger.info(f"Performance Metric: {json.dumps(log_data)}")
    
    def log_cache_stats(self, hit_rate: float, total_size_mb: float, 
                       entries: int):
        """Log cache performance statistics."""
        self.log_metric('cache_hit_rate', hit_rate, 'percent')
        self.log_metric('cache_size', total_size_mb, 'MB')
        self.log_metric('cache_entries', entries, 'count')

import json

def main():
    """Test logging configuration."""
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup logging
        logger = setup_production_logging(
            log_level='DEBUG',
            log_dir=Path(temp_dir)
        )
        
        print("📝 LOGGING CONFIGURATION TEST")
        print("=" * 50)
        
        # Test different log levels
        logger.debug("Debug message - detailed information")
        logger.info("Info message - general information")
        logger.warning("Warning message - potential issue")
        logger.error("Error message - something went wrong")
        
        # Test API request logger
        api_logger = APIRequestLogger()
        api_logger.log_request(
            api_name='copernicus',
            endpoint='/subset',
            params={'lat': 40.0, 'lon': -70.0},
            response_time=0.125,
            status='success'
        )
        
        # Test performance logger
        perf_logger = PerformanceLogger()
        perf_logger.log_metric('api_response_time', 125.5, 'ms', 
                              tags={'api': 'copernicus', 'endpoint': 'subset'})
        perf_logger.log_cache_stats(hit_rate=85.5, total_size_mb=45.2, entries=1250)
        
        print(f"\n✅ Log files created in: {temp_dir}")
        
        # List created log files
        log_files = list(Path(temp_dir).glob('*.log'))
        print("\n📄 Log files created:")
        for log_file in log_files:
            size = log_file.stat().st_size
            print(f"  - {log_file.name} ({size} bytes)")

if __name__ == "__main__":
    main()