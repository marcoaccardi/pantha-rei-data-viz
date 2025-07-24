#!/usr/bin/env python3
"""
Real Data WebSocket Server for NOAA Climate Data Globe
Provides real ocean data using dynamic coordinate system - NO SYNTHETIC DATA.

This server replaces the simple_websocket_server.py to eliminate synthetic data
generation and provide real ERDDAP-based ocean data for any global coordinates.
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime
from pathlib import Path
import sys

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.dynamic_coordinate_system import DynamicOceanDataSystem
from src.utils.coordinate_system import validate_wgs84_coordinates

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealDataWebSocketServer:
    """WebSocket server providing real ocean data without synthetic fallbacks."""

    def __init__(self):
        """Initialize server with dynamic ocean data system."""
        self.clients = set()
        self.dynamic_system = DynamicOceanDataSystem()
        
        logger.info("🌊 Real Data WebSocket Server initialized")
        logger.info("📡 Data Sources: NOAA ERDDAP, PacIOOS, CoastWatch")
        logger.info("❌ Synthetic data generation: DISABLED")
        logger.info("🌍 Coverage: Global ocean coordinates")

    async def register_client(self, websocket):
        """Register a new client connection."""
        self.clients.add(websocket)
        client_ip = websocket.remote_address[0] if websocket.remote_address else "unknown"
        logger.info(f"🔌 Client connected from {client_ip}. Total clients: {len(self.clients)}")
        
        # Send connection confirmation with system info
        await self.send_message(websocket, {
            "type": "connection",
            "payload": {
                "message": "Connected to Real Data NOAA WebSocket Server",
                "timestamp": datetime.now().isoformat(),
                "system_info": {
                    "data_policy": "Real data only - No synthetic generation",
                    "coordinate_system": "WGS84 (EPSG:4326)",
                    "supported_parameters": self.dynamic_system.get_supported_parameters(),
                    "processors": self.dynamic_system.get_supported_processors()
                }
            }
        })

    async def unregister_client(self, websocket):
        """Unregister a client connection."""
        self.clients.discard(websocket)
        logger.info(f"🔌 Client disconnected. Total clients: {len(self.clients)}")

    async def send_message(self, websocket, message):
        """Send a message to a specific client."""
        try:
            await websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            await self.unregister_client(websocket)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    async def handle_coordinate_request(self, websocket, payload):
        """Handle coordinate data request from frontend - REAL DATA ONLY."""
        try:
            # Extract coordinates from request
            lat = float(payload.get('lat', payload.get('latitude', 0)))
            lng = float(payload.get('lng', payload.get('longitude', 0)))
            date = payload.get('date')
            requested_params = payload.get('parameters', ['sea_surface_temperature', 'ocean_currents'])

            logger.info(f"📍 Coordinate request: {lat:.6f}°N, {lng:.6f}°E")

            # Validate coordinates first
            coord_validation = validate_wgs84_coordinates(lat, lng, strict_ocean=False)
            
            if not coord_validation.is_valid:
                await self.send_message(websocket, {
                    "type": "error",
                    "payload": {
                        "message": f"Invalid coordinates: {'; '.join(coord_validation.validation_errors)}",
                        "coordinates": {"lat": lat, "lng": lng},
                        "timestamp": datetime.now().isoformat()
                    }
                })
                return

            # Log coordinate validation results
            ocean_status = "🌊 OCEAN" if coord_validation.is_over_ocean else "🏞️ LAND"
            logger.info(f"   {ocean_status} (confidence: {coord_validation.ocean_confidence:.1%})")

            # Get real ocean data using dynamic system
            logger.info(f"📡 Fetching real data for {len(requested_params)} parameters...")
            
            ocean_data = await self.dynamic_system.get_ocean_data_for_coordinates(
                lat, lng, date, requested_params
            )

            # Transform data to match frontend expectations
            formatted_data = await self.format_for_frontend(ocean_data, lat, lng)

            # Send successful response
            await self.send_message(websocket, {
                "type": "oceanData",
                "payload": formatted_data
            })

            success_count = ocean_data['data_summary']['successful_retrievals']
            total_count = len(requested_params)
            logger.info(f"✅ Response sent: {success_count}/{total_count} parameters successful")

        except Exception as e:
            error_msg = f"Failed to process coordinate request: {str(e)}"
            logger.error(error_msg)
            
            await self.send_message(websocket, {
                "type": "error",
                "payload": {
                    "message": error_msg,
                    "coordinates": {"lat": lat, "lng": lng},
                    "timestamp": datetime.now().isoformat()
                }
            })

    async def format_for_frontend(self, ocean_data: dict, lat: float, lng: float) -> dict:
        """Format ocean data response for frontend consumption."""
        
        # Extract coordinate info
        coord_info = ocean_data['coordinate_info']
        data_results = ocean_data['ocean_data']
        
        # Build measurements list in expected format
        measurements = []
        
        for param_name, param_data in data_results.items():
            if 'data' in param_data:
                data_values = param_data['data']
                metadata = param_data['metadata']
                
                # Handle different parameter types
                if param_name == 'sea_surface_temperature':
                    measurements.extend(self.format_temperature_data(data_values, metadata))
                elif param_name == 'ocean_currents':
                    measurements.extend(self.format_currents_data(data_values, metadata))
                elif param_name == 'marine_bio' or param_name == 'chlorophyll':
                    measurements.extend(self.format_bio_data(data_values, metadata))
                elif param_name == 'wave_data':
                    measurements.extend(self.format_wave_data(data_values, metadata))
                elif param_name == 'coral_bleaching':
                    measurements.extend(self.format_coral_data(data_values, metadata))

        # Create response matching expected frontend format
        return {
            "coordinates": {
                "lat": coord_info['validated_coordinates']['latitude'],
                "lng": coord_info['validated_coordinates']['longitude']
            },
            "ocean_validation": coord_info['ocean_validation'],
            "measurements": measurements,
            "data_summary": ocean_data['data_summary'],
            "timestamp": datetime.now().isoformat(),
            "system": "RealDataWebSocketServer",
            "data_policy": "Real ERDDAP data only - No synthetic generation"
        }

    def format_temperature_data(self, data: dict, metadata: dict) -> list:
        """Format sea surface temperature data."""
        measurements = []
        
        if 'analysed_sst' in data:
            temp_data = data['analysed_sst']
            measurements.append({
                "model": "NOAA_SST_Analysis",
                "parameter": "sea_surface_temperature", 
                "value": temp_data.get('value', 0),
                "units": temp_data.get('units', '°C'),
                "description": "🌡️ Sea Surface Temperature",
                "source": metadata.get('data_source', 'NOAA/ERDDAP'),
                "quality": "R",  # Real data
                "confidence": 0.9,  # High confidence for real data
                "zone": self.get_climate_zone(metadata.get('request_coordinates', {}).get('latitude', 0))
            })
        
        return measurements

    def format_currents_data(self, data: dict, metadata: dict) -> list:
        """Format ocean currents data."""
        measurements = []
        
        if 'u' in data and 'v' in data:
            u_val = data['u'].get('value', 0)
            v_val = data['v'].get('value', 0)
            
            # Calculate speed and direction
            speed = (u_val**2 + v_val**2)**0.5
            
            measurements.append({
                "model": "OSCAR_Ocean_Currents",
                "parameter": "ocean_current_speed",
                "value": round(speed, 3),
                "units": "m/s", 
                "description": "🌊 Ocean Current Speed",
                "source": metadata.get('data_source', 'NOAA/OSCAR'),
                "quality": "R",  # Real data
                "confidence": 0.85,
                "zone": "Marine"
            })
        
        return measurements

    def format_bio_data(self, data: dict, metadata: dict) -> list:
        """Format marine biology/biogeochemistry data."""
        measurements = []
        
        # Handle chlorophyll data
        if 'chlorophyll' in data:
            chl_data = data['chlorophyll']
            measurements.append({
                "model": "Marine_Biology_Model",
                "parameter": "chlorophyll_a_concentration",
                "value": chl_data.get('value', 0),
                "units": chl_data.get('units', 'mg/m³'),
                "description": "📊 Chlorophyll-a Concentration", 
                "source": metadata.get('data_source', 'NOAA/CoastWatch'),
                "quality": "R",  # Real data
                "confidence": 0.8,
                "zone": "Marine"
            })
        
        return measurements

    def format_wave_data(self, data: dict, metadata: dict) -> list:
        """Format wave data."""
        measurements = []
        
        if 'significant_wave_height' in data:
            wave_data = data['significant_wave_height']
            measurements.append({
                "model": "Wave_Analysis_Model",
                "parameter": "significant_wave_height",
                "value": wave_data.get('value', 0),
                "units": wave_data.get('units', 'm'),
                "description": "🌊 Significant Wave Height",
                "source": metadata.get('data_source', 'NOAA/WaveWatch'),
                "quality": "R",  # Real data  
                "confidence": 0.85,
                "zone": "Marine"
            })
        
        return measurements

    def format_coral_data(self, data: dict, metadata: dict) -> list:
        """Format coral bleaching data."""
        measurements = []
        
        if 'degree_heating_weeks' in data:
            dhw_data = data['degree_heating_weeks']
            measurements.append({
                "model": "Coral_Reef_Watch",
                "parameter": "degree_heating_weeks",
                "value": dhw_data.get('value', 0),
                "units": dhw_data.get('units', '°C-weeks'),
                "description": "🪸 Coral Bleaching Risk",
                "source": metadata.get('data_source', 'NOAA/Coral Reef Watch'),
                "quality": "R",  # Real data
                "confidence": 0.9,
                "zone": "Coral Reef"
            })
        
        return measurements

    def get_climate_zone(self, lat: float) -> str:
        """Determine climate zone based on latitude."""
        abs_lat = abs(lat)
        if abs_lat < 23.5:
            return "Tropical"
        elif abs_lat < 35:
            return "Subtropical"
        elif abs_lat < 60:
            return "Temperate"
        else:
            return "Polar"

    async def handle_message(self, websocket):
        """Handle incoming WebSocket messages."""
        try:
            await self.register_client(websocket)
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type')
                    
                    logger.debug(f"📨 Received message type: {message_type}")
                    
                    if message_type == 'getOceanData':
                        await self.handle_coordinate_request(websocket, data.get('payload', {}))
                    elif message_type == 'ping':
                        await self.send_message(websocket, {"type": "pong", "payload": {}})
                    else:
                        logger.warning(f"Unknown message type: {message_type}")
                        
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client connection closed")
        finally:
            await self.unregister_client(websocket)

    async def start_server(self, host='localhost', port=8765):
        """Start the WebSocket server."""
        logger.info(f"🚀 Starting Real Data WebSocket Server on {host}:{port}")
        logger.info("🌊 Providing real ocean data for global coordinates")
        logger.info("❌ Synthetic data generation: DISABLED")
        
        async with websockets.serve(self.handle_message, host, port):
            logger.info(f"✅ Server running on ws://{host}:{port}")
            await asyncio.Future()  # Run forever

    async def shutdown(self):
        """Shutdown server and cleanup resources."""
        logger.info("🔄 Shutting down Real Data WebSocket Server")
        await self.dynamic_system.close()

async def main():
    """Main server entry point."""
    server = RealDataWebSocketServer()
    
    try:
        await server.start_server('localhost', 8765)
    except KeyboardInterrupt:
        logger.info("⏹️ Server shutdown requested")
    finally:
        await server.shutdown()

if __name__ == "__main__":
    # Run the real data server
    print("🌊 NOAA Real Data WebSocket Server")
    print("=" * 50)
    print("📡 Real ERDDAP ocean data - No synthetic generation")
    print("🌍 Global coordinate support")
    print("⚡ Starting server...")
    
    asyncio.run(main())