#!/usr/bin/env python3
"""
NOAA WebSocket Server
Real-time communication server for Globe visualization integration
"""

import asyncio
import websockets
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Set, Any, Optional
import logging

# Add the parent directory to the path to import the NOAA system
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from main import NOAATextureSystem
    from src.processors.enhanced_climate_data import EnhancedClimateDataProcessor
    from src.processors.fast_climate_processor import FastClimateProcessor
except ImportError as e:
    print(f"❌ Failed to import NOAA system: {e}")
    print("Make sure you're running this from the NOAA project directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NOAAWebSocketServer:
    """WebSocket server for real-time NOAA data and texture streaming."""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # Initialize NOAA system
        try:
            self.noaa_system = NOAATextureSystem()
            self.fast_processor = FastClimateProcessor()
            logger.info("✅ NOAA Texture System initialized")
            logger.info("🚀 Fast Climate Processor initialized")
            
            # Verify ocean data system is properly initialized
            if hasattr(self.fast_processor, 'ocean_downloader') and self.fast_processor.ocean_downloader:
                logger.info("🌊 Ocean pollution data system: ✅ Ready")
            else:
                logger.warning("🌊 Ocean pollution data system: ⚠️ Not available - using fallback estimates")
        except Exception as e:
            logger.error(f"❌ Failed to initialize NOAA system: {e}")
            raise
        
        # Track active requests
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"🌐 NOAA WebSocket Server ready on {host}:{port}")
    
    async def register_client(self, websocket: websockets.WebSocketServerProtocol):
        """Register a new client connection."""
        self.clients.add(websocket)
        client_addr = websocket.remote_address
        logger.info(f"👋 Client connected: {client_addr}")
        
        # Send welcome message
        await self.send_message(websocket, {
            "type": "connection",
            "payload": {
                "message": "Connected to NOAA Climate Data System",
                "server_version": "1.0.0",
                "capabilities": [
                    "coordinate_data",
                    "sst_textures", 
                    "climate_analysis",
                    "real_time_updates"
                ],
                "timestamp": datetime.now().isoformat()
            }
        })
    
    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol):
        """Unregister a client connection."""
        self.clients.discard(websocket)
        client_addr = websocket.remote_address
        logger.info(f"👋 Client disconnected: {client_addr}")
    
    async def send_message(self, websocket: websockets.WebSocketServerProtocol, message: Dict[str, Any]):
        """Send a message to a specific client."""
        try:
            await websocket.send(json.dumps(message))
        except websockets.ConnectionClosed:
            await self.unregister_client(websocket)
        except Exception as e:
            logger.error(f"❌ Failed to send message: {e}")
    
    async def broadcast_message(self, message: Dict[str, Any], exclude: Optional[Set] = None):
        """Broadcast a message to all connected clients."""
        if not self.clients:
            return
        
        exclude = exclude or set()
        targets = self.clients - exclude
        
        if targets:
            await asyncio.gather(
                *[self.send_message(client, message) for client in targets],
                return_exceptions=True
            )
    
    async def send_progress_update(self, websocket: websockets.WebSocketServerProtocol, progress: int, message: str):
        """Send a progress update to a client."""
        await self.send_message(websocket, {
            "type": "progress",
            "payload": {
                "progress": progress,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        })
    
    async def send_keepalive(self, websocket: websockets.WebSocketServerProtocol):
        """Send a keepalive ping to maintain connection during processing."""
        try:
            await websocket.ping()
            logger.debug(f"📡 Sent keepalive ping to {websocket.remote_address}")
            return True
        except websockets.ConnectionClosed:
            logger.warning(f"⚠️ Cannot send keepalive - connection closed: {websocket.remote_address}")
            return False
        except Exception as e:
            logger.error(f"❌ Error sending keepalive: {e}")
            return False
    
    async def periodic_keepalive(self, websocket: websockets.WebSocketServerProtocol, interval: int = 10):
        """Send periodic keepalive pings during long operations."""
        try:
            while True:
                await asyncio.sleep(interval)
                if not await self.send_keepalive(websocket):
                    break  # Connection lost, stop sending keepalives
        except asyncio.CancelledError:
            logger.debug(f"🛑 Keepalive task cancelled for {websocket.remote_address}")
            raise
        except Exception as e:
            logger.error(f"❌ Periodic keepalive error: {e}")
    
    async def handle_coordinate_request(self, websocket: websockets.WebSocketServerProtocol, payload: Dict[str, Any]):
        """Handle coordinate-based data request."""
        try:
            coordinates = payload.get("coordinates", {})
            lat = coordinates.get("lat")
            lng = coordinates.get("lng")
            
            if lat is None or lng is None:
                await self.send_message(websocket, {
                    "type": "error",
                    "payload": {
                        "message": "Invalid coordinates provided",
                        "timestamp": datetime.now().isoformat()
                    }
                })
                return
            
            # Validate coordinate bounds
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                await self.send_message(websocket, {
                    "type": "error",
                    "payload": {
                        "message": "Coordinates out of valid range",
                        "timestamp": datetime.now().isoformat()
                    }
                })
                return
            
            request_id = f"{lat:.4f},{lng:.4f}_{datetime.now().timestamp()}"
            self.active_requests[request_id] = {
                "websocket": websocket,
                "coordinates": coordinates,
                "start_time": datetime.now()
            }
            
            logger.info(f"🎯 Processing coordinate request: {lat:.4f}, {lng:.4f}")
            
            # Step 1: Send initial progress
            await self.send_progress_update(websocket, 10, "Initializing climate data collection...")
            await self.send_keepalive(websocket)
            
            # Step 2: Collect climate data (long operation - send keepalives)
            await self.send_progress_update(websocket, 30, "Collecting comprehensive climate data...")
            
            # Use fast climate data collection with timeout
            try:
                climate_data_list = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, 
                        self.collect_climate_data_fast,
                        lat, lng
                    ),
                    timeout=20.0  # Maximum 20 seconds total
                )
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Climate data collection timeout, using emergency fallback")
                climate_data_list = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.emergency_fallback_data,
                    lat, lng
                )
            
            # Step 3: Send climate data
            await self.send_progress_update(websocket, 60, "Climate data collected, processing SST texture...")
            
            await self.send_message(websocket, {
                "type": "climate_data", 
                "payload": {
                    "coordinates": coordinates,
                    "climateData": climate_data_list,
                    "timestamp": datetime.now().isoformat()
                }
            })
            
            # Step 4: Generate SST texture (another long operation)
            await self.send_progress_update(websocket, 80, "Generating SST texture...")
            await self.send_keepalive(websocket)
            
            # Create task for texture generation with keepalives
            async def generate_with_keepalive():
                keepalive_task = asyncio.create_task(self.periodic_keepalive(websocket, interval=5))
                try:
                    texture_path = await asyncio.get_event_loop().run_in_executor(
                        None,
                        self.generate_sst_texture,
                        lat, lng
                    )
                    return texture_path
                finally:
                    keepalive_task.cancel()
                    try:
                        await keepalive_task
                    except asyncio.CancelledError:
                        pass
            
            texture_path = await generate_with_keepalive()
            
            # Step 5: Send texture update
            await self.send_progress_update(websocket, 100, "Data processing complete!")
            
            if texture_path:
                # Convert absolute path to web-accessible path
                web_texture_path = self.convert_to_web_path(texture_path)
                
                await self.send_message(websocket, {
                    "type": "texture_update",
                    "payload": {
                        "coordinates": coordinates,
                        "texturePath": web_texture_path,
                        "timestamp": datetime.now().isoformat()
                    }
                })
                
                logger.info(f"✅ Completed coordinate request: {lat:.4f}, {lng:.4f}")
            else:
                await self.send_message(websocket, {
                    "type": "error",
                    "payload": {
                        "message": "Failed to generate SST texture",
                        "timestamp": datetime.now().isoformat()
                    }
                })
            
            # Cleanup request
            if request_id in self.active_requests:
                del self.active_requests[request_id]
                
        except Exception as e:
            logger.error(f"❌ Error processing coordinate request: {e}")
            await self.send_message(websocket, {
                "type": "error",
                "payload": {
                    "message": f"Server error: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
            })
    
    def collect_climate_data(self, lat: float, lng: float) -> list:
        """Collect climate data synchronously (runs in executor)."""
        try:
            logger.info(f"🌍 Starting climate data collection for {lat:.4f}, {lng:.4f}")
            
            # Get comprehensive climate data
            climate_data = self.noaa_system.enhanced_climate_processor.get_comprehensive_climate_data(lat, lng)
            
            logger.info(f"📊 Climate data collected - Zone: {climate_data.climate_zone}")
            
            # Export to CSV for reference
            try:
                csv_file = self.noaa_system.enhanced_climate_processor.export_climate_data(climate_data)
                logger.info(f"📁 Data exported to: {csv_file}")
            except Exception as csv_error:
                logger.warning(f"⚠️ CSV export failed: {csv_error}")
            
            # Convert climate data to list format for JSON serialization
            climate_data_list = []
            
            # Always add basic location and climate info
            basic_info = {
                "latitude": lat,
                "longitude": lng,
                "date": climate_data.date,
                "data_source": "Basic_Info",
                "parameter": "climate_zone",
                "value": climate_data.climate_zone,
                "units": "",
                "description": f"Climate zone classification",
                "quality": "Derived",
                "confidence": 1.0,
                "climate_zone": climate_data.climate_zone,
                "weather_labels": climate_data.weather_labels,
                "timestamp": datetime.now().isoformat()
            }
            climate_data_list.append(basic_info)
            
            # Add current weather data
            if hasattr(climate_data, 'current_weather') and climate_data.current_weather:
                logger.info(f"🌡️ Processing {len(climate_data.current_weather)} weather parameters")
                for param, data in climate_data.current_weather.items():
                    if isinstance(data, dict) and 'value' in data:
                        climate_data_list.append({
                            "latitude": lat,
                            "longitude": lng,
                            "date": climate_data.date,
                            "data_source": "Current_Weather",
                            "parameter": param,
                            "value": data['value'],
                            "units": data.get('unit', ''),
                            "description": data.get('description', param),
                            "quality": data.get('quality_control', 'Unknown'),
                            "confidence": data.get('confidence', 0.5),
                            "climate_zone": climate_data.climate_zone,
                            "weather_labels": climate_data.weather_labels,
                            "timestamp": datetime.now().isoformat()
                        })
            
            # Add marine data if available
            marine_sources = [
                ('coral_bleaching_data', 'Coral_Bleaching'),
                ('wave_data', 'Wave_Data'),
                ('ocean_currents', 'Ocean_Currents'),
                ('marine_biogeochemistry', 'Marine_Bio')
            ]
            
            for attr_name, source_name in marine_sources:
                if hasattr(climate_data, attr_name):
                    marine_data = getattr(climate_data, attr_name)
                    if marine_data and isinstance(marine_data, dict):
                        # Add a few key parameters from each marine data source
                        count = 0
                        for param, data in marine_data.items():
                            if isinstance(data, dict) and 'value' in data and count < 3:
                                climate_data_list.append({
                                    "latitude": lat,
                                    "longitude": lng,
                                    "date": climate_data.date,
                                    "data_source": source_name,
                                    "parameter": param,
                                    "value": data['value'],
                                    "units": data.get('units', ''),
                                    "description": data.get('description', param),
                                    "quality": marine_data.get('metadata', {}).get('source', 'Unknown'),
                                    "confidence": 0.8,
                                    "climate_zone": climate_data.climate_zone,
                                    "weather_labels": climate_data.weather_labels,
                                    "timestamp": datetime.now().isoformat()
                                })
                                count += 1
            
            # Add gridded data
            if hasattr(climate_data, 'gridded_data') and climate_data.gridded_data:
                variables = climate_data.gridded_data.get('variables', {})
                for param, value in list(variables.items())[:5]:  # Limit to 5 items
                    climate_data_list.append({
                        "latitude": lat,
                        "longitude": lng,
                        "date": climate_data.date,
                        "data_source": "Gridded_Analysis",
                        "parameter": param,
                        "value": value,
                        "units": "Various",
                        "description": f"Gridded analysis {param}",
                        "quality": "Interpolated",
                        "confidence": 0.7,
                        "climate_zone": climate_data.climate_zone,
                        "weather_labels": climate_data.weather_labels,
                        "timestamp": datetime.now().isoformat()
                    })
            
            logger.info(f"✅ Climate data formatted: {len(climate_data_list)} parameters")
            return climate_data_list[:25]  # Limit to first 25 items for web display
            
        except Exception as e:
            logger.error(f"❌ Error collecting climate data: {e}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            
            # Return at least some basic info even if collection fails
            fallback_data = [{
                "latitude": lat,
                "longitude": lng,
                "date": datetime.now().strftime('%Y-%m-%d'),
                "data_source": "Error_Fallback",
                "parameter": "error_message",
                "value": str(e),
                "units": "",
                "description": "Data collection failed",
                "quality": "Error",
                "confidence": 0.0,
                "climate_zone": "unknown",
                "weather_labels": ["error"],
                "timestamp": datetime.now().isoformat()
            }]
            return fallback_data
    
    def collect_climate_data_fast(self, lat: float, lng: float) -> list:
        """Fast climate data collection with guaranteed response."""
        try:
            logger.info(f"🚀 Fast climate data collection for {lat:.4f}, {lng:.4f}")
            
            # Use the fast processor
            climate_data = self.fast_processor.get_climate_data_fast(lat, lng)
            
            # Convert to list format for JSON serialization
            climate_data_list = []
            
            # Add basic info
            climate_data_list.append({
                "latitude": lat,
                "longitude": lng,
                "date": climate_data['date'],
                "data_source": "Location_Info",
                "parameter": "climate_zone",
                "value": climate_data['climate_zone'],
                "units": "",
                "description": f"Climate zone: {climate_data['climate_zone']}",
                "quality": "Derived",
                "confidence": 1.0,
                "climate_zone": climate_data['climate_zone'],
                "weather_labels": climate_data['weather_labels'],
                "timestamp": datetime.now().isoformat()
            })
            
            # Add current weather data
            for param, data in climate_data['current_weather'].items():
                climate_data_list.append({
                    "latitude": lat,
                    "longitude": lng,
                    "date": climate_data['date'],
                    "data_source": "Weather",
                    "parameter": param,
                    "value": data['value'],
                    "units": data['units'],
                    "description": f"Current {param.replace('_', ' ')}",
                    "quality": data['quality'],
                    "confidence": 0.8 if data['source'] != 'Estimated' else 0.6,
                    "climate_zone": climate_data['climate_zone'],
                    "weather_labels": climate_data['weather_labels'],
                    "timestamp": datetime.now().isoformat()
                })
            
            # Add marine data with proper categorization
            for param, data in climate_data['marine_data'].items():
                # Categorize parameters into different data sources
                if param in ['ocean_ph', 'dissolved_oxygen', 'co2_seawater']:
                    data_source = "Ocean_Chemistry"
                elif param in ['microplastics_density', 'dominant_polymer']:
                    data_source = "Marine_Pollution"
                elif param in ['wave_height', 'wave_period', 'current_speed', 'current_direction']:
                    data_source = "Marine"
                elif param in ['chlorophyll', 'coral_stress']:
                    data_source = "Ocean_Health"
                else:
                    data_source = "Marine"
                
                # Format parameter display names
                display_names = {
                    'ocean_ph': 'Ocean pH',
                    'dissolved_oxygen': 'Dissolved Oxygen',
                    'co2_seawater': 'Seawater CO2',
                    'microplastics_density': 'Microplastics Density',
                    'dominant_polymer': 'Dominant Polymer Type',
                    'wave_height': 'Wave Height',
                    'wave_period': 'Wave Period',
                    'current_speed': 'Current Speed',
                    'current_direction': 'Current Direction',
                    'sea_surface_temperature': 'Sea Surface Temperature',
                    'chlorophyll': 'Chlorophyll Concentration',
                    'coral_stress': 'Coral Stress Index'
                }
                
                display_name = display_names.get(param, param.replace('_', ' ').title())
                
                climate_data_list.append({
                    "latitude": lat,
                    "longitude": lng,
                    "date": climate_data['date'],
                    "data_source": data_source,
                    "parameter": param,
                    "value": data['value'],
                    "units": data['units'],
                    "description": display_name,
                    "quality": data['quality'],
                    "confidence": 0.8 if data['source'] in ['NCEI', 'OCADS', 'SOCAT'] else 0.6 if data['source'] != 'Estimated' else 0.5,
                    "climate_zone": climate_data['climate_zone'],
                    "weather_labels": climate_data['weather_labels'],
                    "timestamp": datetime.now().isoformat()
                })
            
            processing_time = climate_data['metadata']['processing_time']
            data_quality = climate_data['metadata']['data_quality']
            
            logger.info(f"✅ Fast climate data ready: {len(climate_data_list)} parameters in {processing_time:.2f}s ({data_quality})")
            return climate_data_list
            
        except Exception as e:
            logger.error(f"❌ Fast climate data collection failed: {e}")
            return self.emergency_fallback_data(lat, lng)
    
    def emergency_fallback_data(self, lat: float, lng: float) -> list:
        """Emergency fallback data when everything else fails."""
        logger.info(f"🆘 Generating emergency fallback data for {lat:.4f}, {lng:.4f}")
        
        # Determine climate zone
        abs_lat = abs(lat)
        if abs_lat <= 23.5:
            climate_zone = 'tropical'
        elif abs_lat <= 35:
            climate_zone = 'subtropical'
        elif abs_lat <= 60:
            climate_zone = 'temperate'
        else:
            climate_zone = 'polar'
        
        emergency_data = [
            {
                "latitude": lat,
                "longitude": lng,
                "date": datetime.now().strftime('%Y-%m-%d'),
                "data_source": "Emergency_Fallback",
                "parameter": "status",
                "value": "Data available",
                "units": "",
                "description": "Emergency fallback - system operational",
                "quality": "Fallback",
                "confidence": 0.5,
                "climate_zone": climate_zone,
                "weather_labels": [climate_zone.title(), "Estimated"],
                "timestamp": datetime.now().isoformat()
            },
            {
                "latitude": lat,
                "longitude": lng,
                "date": datetime.now().strftime('%Y-%m-%d'),
                "data_source": "Emergency_Fallback",
                "parameter": "temperature",
                "value": 20.0 + (25.0 - abs_lat) * 0.5,  # Simple temperature estimate
                "units": "°C",
                "description": "Estimated temperature based on latitude",
                "quality": "Estimated",
                "confidence": 0.4,
                "climate_zone": climate_zone,
                "weather_labels": [climate_zone.title(), "Estimated"],
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        return emergency_data
    
    def generate_sst_texture(self, lat: float, lng: float) -> Optional[str]:
        """Generate SST texture synchronously (runs in executor)."""
        try:
            # Generate SST texture with medium resolution for web
            texture_path = self.noaa_system.run_sst_only(force=False, resolution="medium")
            
            if texture_path and texture_path.exists():
                logger.info(f"✅ SST texture generated: {texture_path}")
                return str(texture_path)
            else:
                logger.warning("⚠️ No SST texture generated")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error generating SST texture: {e}")
            return None
    
    def convert_to_web_path(self, file_path: str) -> str:
        """Convert absolute file path to web-accessible path."""
        try:
            path = Path(file_path)
            
            # Find the textures directory in the path
            parts = path.parts
            if 'textures' in parts:
                textures_index = parts.index('textures')
                web_path = '/' + '/'.join(parts[textures_index:])
                logger.info(f"🔗 Converted texture path: {file_path} -> {web_path}")
                return web_path
            else:
                # Fallback: assume it's in the textures directory
                fallback_path = f"/textures/sst/{path.name}"
                logger.warning(f"⚠️ Using fallback texture path: {fallback_path}")
                return fallback_path
                
        except Exception as e:
            logger.error(f"❌ Error converting path to web format: {e}")
            fallback_path = f"/textures/sst/{Path(file_path).name}"
            logger.error(f"❌ Using error fallback path: {fallback_path}")
            return fallback_path
    
    async def handle_message(self, websocket: websockets.WebSocketServerProtocol, message_str: str):
        """Handle incoming WebSocket message."""
        try:
            message = json.loads(message_str)
            message_type = message.get("type")
            payload = message.get("payload", {})
            
            logger.info(f"📨 Received message type: {message_type}")
            
            if message_type == "coordinate_request" or message_type == "coordinate_data":
                await self.handle_coordinate_request(websocket, payload)
            elif message_type == "ping":
                await self.send_message(websocket, {
                    "type": "pong",
                    "payload": {
                        "timestamp": datetime.now().isoformat()
                    }
                })
            else:
                logger.warning(f"⚠️ Unknown message type: {message_type}")
                await self.send_message(websocket, {
                    "type": "error",
                    "payload": {
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": datetime.now().isoformat()
                    }
                })
                
        except json.JSONDecodeError:
            logger.error("❌ Invalid JSON received")
            await self.send_message(websocket, {
                "type": "error",
                "payload": {
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                }
            })
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")
            await self.send_message(websocket, {
                "type": "error",
                "payload": {
                    "message": f"Message processing error: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
            })
    
    async def client_handler(self, websocket: websockets.WebSocketServerProtocol, path: str = "/"):
        """Handle individual client connections."""
        await self.register_client(websocket)
        
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"❌ Client handler error: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def start_server(self):
        """Start the WebSocket server."""
        logger.info(f"🚀 Starting NOAA WebSocket server on {self.host}:{self.port}")
        
        try:
            # Handler wrapper to handle different websockets API versions
            async def handler_wrapper(websocket, path=None):
                await self.client_handler(websocket, path or "/")
            
            async with websockets.serve(
                handler_wrapper,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=10,
                max_size=1024*1024,  # 1MB max message size
                compression=None
            ):
                logger.info(f"✅ NOAA WebSocket server running on ws://{self.host}:{self.port}")
                logger.info("🌊 Ready to serve real-time climate data and SST textures")
                
                # Keep the server running
                await asyncio.Future()  # Run forever
                
        except Exception as e:
            logger.error(f"❌ Failed to start server: {e}")
            raise
    
    def cleanup(self):
        """Cleanup resources."""
        try:
            if hasattr(self, 'noaa_system'):
                self.noaa_system.cleanup()
            logger.info("✅ Server cleanup complete")
        except Exception as e:
            logger.error(f"⚠️ Cleanup error: {e}")

async def main():
    """Main entry point."""
    server = None
    try:
        server = NOAAWebSocketServer()
        await server.start_server()
    except KeyboardInterrupt:
        logger.info("🛑 Server shutdown requested by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
    finally:
        if server:
            server.cleanup()

if __name__ == "__main__":
    print("🌍 NOAA WebSocket Server")
    print("=" * 50)
    print("Real-time climate data and SST texture streaming")
    print("For React Three Fiber Globe Visualization")
    print("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)