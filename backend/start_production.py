#!/usr/bin/env python3
"""
Production startup script for backend-api ocean climate data system.
This script initializes all components and starts the WebSocket server.
"""

import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

from config.logging_config import setup_production_logging
from servers.climate_data_websocket_server import ClimateDataWebSocketServer
from utils.performance_monitor import PerformanceMonitor
import threading
import signal
import time

# Load environment variables
load_dotenv()
load_dotenv('config/production.env')

# Global flag for graceful shutdown
shutdown_event = threading.Event()

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()

def monitor_system_performance(monitor: PerformanceMonitor):
    """Background thread to monitor system performance."""
    logger = logging.getLogger(__name__)
    logger.info("Starting performance monitoring thread...")
    
    while not shutdown_event.is_set():
        try:
            # Record system metrics every 30 seconds
            monitor.record_system_metrics()
            
            # Save metrics to file every 5 minutes
            if int(time.time()) % 300 == 0:
                monitor.save_metrics()
                
                # Log health status
                health = monitor.get_health_status()
                if health['status'] != 'healthy':
                    logger.warning(f"System health: {health['status']} - {health['issues']}")
            
            # Sleep for 30 seconds
            shutdown_event.wait(30)
            
        except Exception as e:
            logger.error(f"Error in performance monitoring: {e}")
            time.sleep(30)
    
    logger.info("Performance monitoring thread stopped")

async def main():
    """Main startup function."""
    global logger
    
    # Setup logging
    logger = setup_production_logging()
    logger.info("🌊 Starting Backend-API Ocean Climate Data System")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Verify environment (check for both formats)
        copernicus_user = os.getenv('COPERNICUS_USERNAME') or os.getenv('copernicus_username')
        copernicus_pass = os.getenv('COPERNICUS_PASSWORD') or os.getenv('copernicus_password')
        
        if not copernicus_user or not copernicus_pass:
            logger.error("❌ Copernicus credentials not found in environment!")
            logger.error("Please ensure copernicus_username and copernicus_password are set in .env file")
            logger.info("Current environment variables:")
            logger.info(f"  copernicus_username: {'SET' if os.getenv('copernicus_username') else 'NOT SET'}")
            logger.info(f"  copernicus_password: {'SET' if os.getenv('copernicus_password') else 'NOT SET'}")
            sys.exit(1)
        else:
            logger.info("✅ Copernicus credentials found in environment")
        
        # Initialize performance monitor
        metrics_dir = Path('metrics')
        metrics_dir.mkdir(exist_ok=True)
        performance_monitor = PerformanceMonitor(
            metrics_file=metrics_dir / 'performance_metrics.json'
        )
        
        # Start performance monitoring thread
        monitor_thread = threading.Thread(
            target=monitor_system_performance,
            args=(performance_monitor,),
            daemon=True
        )
        monitor_thread.start()
        
        # Initialize and start WebSocket server
        port = int(os.getenv('WEBSOCKET_PORT', 8765))
        server = ClimateDataWebSocketServer(port=port)
        
        logger.info("✅ All systems initialized successfully")
        logger.info(f"🚀 Starting WebSocket server on port {port}")
        logger.info("=" * 60)
        logger.info("System ready for connections!")
        logger.info(f"WebSocket URL: ws://localhost:{port}")
        logger.info("=" * 60)
        
        # Start server
        await server.start()
        
    except KeyboardInterrupt:
        logger.info("Shutdown initiated by user")
    except Exception as e:
        logger.error(f"Fatal error during startup: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Shutting down Backend-API system...")
        shutdown_event.set()

if __name__ == "__main__":
    import logging
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)