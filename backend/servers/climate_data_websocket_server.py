#!/usr/bin/env python3
"""
WebSocket server for real-time ocean climate data streaming.
Integrates with web-globe visualization infrastructure.
"""

import asyncio
import websockets
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from dotenv import load_dotenv

# Add backend directory to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from clients.copernicus_client_production import CopernicusMarineProductionClient
from clients.pangaea_client import PANGAEAClient
from clients.obis_client import OBISClient
from clients.ncei_microplastics_client import NCEIMicroplasticsClient
from utils.coordinate_validator import CoordinateValidator
from utils.cache_manager import APIResponseCache

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ClimateDataWebSocketServer:
    """WebSocket server for ocean climate data streaming."""
    
    def __init__(self, port: int = 8765):
        """Initialize the WebSocket server."""
        self.port = port
        self.clients = set()
        
        # Initialize API clients
        logger.info("Initializing API clients...")
        self.copernicus_client = CopernicusMarineProductionClient()
        self.pangaea_client = PANGAEAClient()
        self.obis_client = OBISClient()
        self.ncei_microplastics_client = NCEIMicroplasticsClient()
        
        # Initialize utilities
        self.coordinate_validator = CoordinateValidator()
        # Use cache in backend directory
        cache_path = Path(__file__).parent.parent / 'cache'
        self.cache = APIResponseCache(cache_path)
        
        logger.info("Climate Data WebSocket Server initialized")
    
    async def handle_temperature_request(self, websocket, message: Dict[str, Any]):
        """Handle real-time temperature data requests with progress notifications."""
        try:
            # Extract and validate coordinates from payload
            payload = message.get('payload', {})
            coordinates = payload.get('coordinates', {})
            lat = coordinates.get('lat')
            lon = coordinates.get('lon')
            
            if not self.coordinate_validator.validate_ocean_point(lat, lon):
                await self._send_error(websocket, "Invalid ocean coordinates")
                return
            
            # Extract date range with proper fallbacks
            date_range = payload.get('dateRange', {})
            start_date = date_range.get('start', '2024-01-01')
            end_date = date_range.get('end', start_date)  # Use same date for single-day queries
            
            # Send initial progress notification
            await self._send_progress(websocket, "Checking cache for ocean data...")
            
            # Check cache first
            cache_key = f"temp_{lat}_{lon}_{start_date}_{end_date}"
            cached_data = self.cache.get_cached_response('copernicus', cache_key)
            
            if cached_data:
                logger.info(f"Returning cached temperature data for {lat}, {lon}")
                await self._send_progress(websocket, "Found cached data - loading immediately")
                
                response = {
                    'type': 'temperature_data',
                    'coordinates': {'lat': lat, 'lon': lon},
                    'data': cached_data,
                    'cached': True,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                # Notify frontend that we're downloading data
                await self._send_progress(websocket, f"Downloading ocean data from Copernicus Marine for {start_date}...")
                logger.info(f"Querying temperature data for {lat}, {lon} on {start_date}")
                
                # Query Copernicus for temperature data
                result = self.copernicus_client.query_data(
                    lat=lat, lon=lon,
                    start_date=start_date,
                    end_date=end_date,
                    dataset_key='sst_global_l4'
                )
                
                if result.get('status') == 'success':
                    # Cache successful responses
                    await self._send_progress(websocket, "Data downloaded successfully - caching for future use...")
                    self.cache.cache_response('copernicus', cache_key, result, ttl_hours=24)
                    logger.info(f"Cached temperature data for {lat}, {lon}")
                else:
                    await self._send_progress(websocket, "Data download completed with warnings")
                
                # Format response for web-globe
                response = {
                    'type': 'temperature_data',
                    'coordinates': {'lat': lat, 'lon': lon},
                    'data': result,
                    'cached': False,
                    'timestamp': datetime.now().isoformat()
                }
            
            await websocket.send(json.dumps(response, default=str))
            
        except Exception as e:
            logger.error(f"Error handling temperature request: {e}")
            await self._send_error(websocket, f"Temperature data query failed: {str(e)}")
    
    async def handle_salinity_request(self, websocket, message: Dict[str, Any]):
        """Handle salinity data requests."""
        try:
            # Extract and validate coordinates from payload
            payload = message.get('payload', {})
            coordinates = payload.get('coordinates', {})
            lat = coordinates.get('lat')
            lon = coordinates.get('lon')
            
            if not self.coordinate_validator.validate_ocean_point(lat, lon):
                await self._send_error(websocket, "Invalid ocean coordinates")
                return
            
            # Extract date range with proper fallbacks
            date_range = payload.get('dateRange', {})
            start_date = date_range.get('start', '2024-01-01')
            end_date = date_range.get('end', start_date)
            
            result = self.copernicus_client.query_data(
                lat=lat, lon=lon,
                start_date=start_date,
                end_date=end_date,
                dataset_key='salinity_global'
            )
            
            response = {
                'type': 'salinity_data',
                'coordinates': {'lat': lat, 'lon': lon},
                'data': result,
                'timestamp': datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(response, default=str))
            
        except Exception as e:
            logger.error(f"Error handling salinity request: {e}")
            await self._send_error(websocket, f"Salinity data query failed: {str(e)}")
    
    async def handle_wave_request(self, websocket, message: Dict[str, Any]):
        """Handle wave height and period data requests."""
        try:
            # Extract and validate coordinates from payload
            payload = message.get('payload', {})
            coordinates = payload.get('coordinates', {})
            lat = coordinates.get('lat')
            lon = coordinates.get('lon')
            
            if not self.coordinate_validator.validate_ocean_point(lat, lon):
                await self._send_error(websocket, "Invalid ocean coordinates")
                return
            
            # Extract date range with proper fallbacks
            date_range = payload.get('dateRange', {})
            start_date = date_range.get('start', '2024-01-01')
            end_date = date_range.get('end', start_date)
            
            result = self.copernicus_client.query_data(
                lat=lat, lon=lon,
                start_date=start_date,
                end_date=end_date,
                dataset_key='wave_global'
            )
            
            response = {
                'type': 'wave_data',
                'coordinates': {'lat': lat, 'lon': lon},
                'data': result,
                'timestamp': datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(response, default=str))
            
        except Exception as e:
            logger.error(f"Error handling wave request: {e}")
            await self._send_error(websocket, f"Wave data query failed: {str(e)}")
    
    async def handle_currents_request(self, websocket, message: Dict[str, Any]):
        """Handle ocean currents data requests."""
        try:
            # Extract and validate coordinates from payload
            payload = message.get('payload', {})
            coordinates = payload.get('coordinates', {})
            lat = coordinates.get('lat')
            lon = coordinates.get('lon')
            
            if not self.coordinate_validator.validate_ocean_point(lat, lon):
                await self._send_error(websocket, "Invalid ocean coordinates")
                return
            
            # Extract date range with proper fallbacks
            date_range = payload.get('dateRange', {})
            start_date = date_range.get('start', '2024-01-01')
            end_date = date_range.get('end', start_date)
            
            result = self.copernicus_client.query_data(
                lat=lat, lon=lon,
                start_date=start_date,
                end_date=end_date,
                dataset_key='currents_global'
            )
            
            response = {
                'type': 'currents_data',
                'coordinates': {'lat': lat, 'lon': lon},
                'data': result,
                'timestamp': datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(response, default=str))
            
        except Exception as e:
            logger.error(f"Error handling currents request: {e}")
            await self._send_error(websocket, f"Currents data query failed: {str(e)}")
    
    async def handle_chlorophyll_request(self, websocket, message: Dict[str, Any]):
        """Handle chlorophyll/plankton concentration requests."""
        try:
            # Extract and validate coordinates from payload
            payload = message.get('payload', {})
            coordinates = payload.get('coordinates', {})
            lat = coordinates.get('lat')
            lon = coordinates.get('lon')
            
            if not self.coordinate_validator.validate_ocean_point(lat, lon):
                await self._send_error(websocket, "Invalid ocean coordinates")
                return
            
            # Extract date range with proper fallbacks
            date_range = payload.get('dateRange', {})
            start_date = date_range.get('start', '2024-01-01')
            end_date = date_range.get('end', start_date)
            
            result = self.copernicus_client.query_data(
                lat=lat, lon=lon,
                start_date=start_date,
                end_date=end_date,
                dataset_key='chlorophyll_global'
            )
            
            response = {
                'type': 'chlorophyll_data',
                'coordinates': {'lat': lat, 'lon': lon},
                'data': result,
                'timestamp': datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(response, default=str))
            
        except Exception as e:
            logger.error(f"Error handling chlorophyll request: {e}")
            await self._send_error(websocket, f"Chlorophyll data query failed: {str(e)}")
    
    async def handle_ph_request(self, websocket, message: Dict[str, Any]):
        """Handle pH/ocean acidification requests."""
        try:
            # Extract and validate coordinates from payload
            payload = message.get('payload', {})
            coordinates = payload.get('coordinates', {})
            lat = coordinates.get('lat')
            lon = coordinates.get('lon')
            
            if not self.coordinate_validator.validate_ocean_point(lat, lon):
                await self._send_error(websocket, "Invalid ocean coordinates")
                return
            
            # Extract date range with proper fallbacks
            date_range = payload.get('dateRange', {})
            start_date = date_range.get('start', '2024-01-01')
            end_date = date_range.get('end', start_date)
            
            result = self.copernicus_client.query_data(
                lat=lat, lon=lon,
                start_date=start_date,
                end_date=end_date,
                dataset_key='ph_global'
            )
            
            response = {
                'type': 'ph_data',
                'coordinates': {'lat': lat, 'lon': lon},
                'data': result,
                'timestamp': datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(response, default=str))
            
        except Exception as e:
            logger.error(f"Error handling pH request: {e}")
            await self._send_error(websocket, f"pH data query failed: {str(e)}")
    
    async def handle_biodiversity_request(self, websocket, message: Dict[str, Any]):
        """Handle marine biodiversity data requests using OBIS API."""
        try:
            # Extract and validate coordinates from payload
            payload = message.get('payload', {})
            coordinates = payload.get('coordinates', {})
            lat = coordinates.get('lat')
            lon = coordinates.get('lon')
            
            if not self.coordinate_validator.validate_ocean_point(lat, lon):
                await self._send_error(websocket, "Invalid ocean coordinates")
                return
            
            # Extract date range with proper fallbacks
            date_range = payload.get('dateRange', {})
            start_date = date_range.get('start', '2020-01-01')
            end_date = date_range.get('end', start_date or '2024-12-31')
            
            # Query OBIS for reliable biodiversity data
            result = self.obis_client.query_data(
                lat=lat, 
                lon=lon,
                start_date=start_date,
                end_date=end_date,
                radius=payload.get('radius', 50)  # 50km default radius
            )
            
            response = {
                'type': 'biodiversity_data',
                'coordinates': coordinates,
                'data': result,
                'timestamp': datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(response, default=str))
            
        except Exception as e:
            logger.error(f"Error handling biodiversity request: {e}")
            await self._send_error(websocket, f"Biodiversity query failed: {str(e)}")
    
    async def handle_microplastics_request(self, websocket, message: Dict[str, Any]):
        """Handle microplastics data requests using NCEI database."""
        try:
            # Extract and validate coordinates from payload
            payload = message.get('payload', {})
            coordinates = payload.get('coordinates', {})
            lat = coordinates.get('lat')
            lon = coordinates.get('lon')
            
            if not self.coordinate_validator.validate_ocean_point(lat, lon):
                await self._send_error(websocket, "Invalid ocean coordinates")
                return
            
            # Extract date range with proper fallbacks
            date_range = payload.get('dateRange', {})
            start_date = date_range.get('start', '2020-01-01')
            end_date = date_range.get('end', start_date or '2024-12-31')
            
            # Query NCEI for reliable microplastics data
            logger.info(f"Querying NCEI microplastics data for {lat}, {lon}")
            
            result = self.ncei_microplastics_client.query_data(
                lat=lat, 
                lon=lon,
                start_date=start_date,
                end_date=end_date,
                radius=payload.get('radius', 100)  # 100km default radius
            )
            
            response = {
                'type': 'microplastics_data',
                'coordinates': coordinates,
                'data': result,
                'timestamp': datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(response, default=str))
            
        except Exception as e:
            logger.error(f"Error handling microplastics request: {e}")
            await self._send_error(websocket, f"Microplastics query failed: {str(e)}")
    
    async def handle_coverage_request(self, websocket, message: Dict[str, Any]):
        """Handle data coverage information requests."""
        try:
            payload = message.get('payload', {})
            api_name = payload.get('api', 'copernicus')
            
            if api_name == 'copernicus':
                coverage = self.copernicus_client.discover_coverage()
            elif api_name == 'pangaea':
                coverage = self.pangaea_client.discover_coverage()
            else:
                await self._send_error(websocket, f"Unknown API: {api_name}")
                return
            
            response = {
                'type': 'coverage_data',
                'api': api_name,
                'data': coverage,
                'timestamp': datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(response, default=str))
            
        except Exception as e:
            logger.error(f"Error handling coverage request: {e}")
            await self._send_error(websocket, f"Coverage query failed: {str(e)}")
    
    async def handle_client(self, websocket, path):
        """Handle WebSocket client connections."""
        # Register client
        self.clients.add(websocket)
        client_id = id(websocket)
        logger.info(f"Client {client_id} connected. Total clients: {len(self.clients)}")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type')
                    
                    logger.info(f"Received message type: {message_type} from client {client_id}")
                    
                    if message_type == 'temperature_request':
                        await self.handle_temperature_request(websocket, data)
                    elif message_type == 'salinity_request':
                        await self.handle_salinity_request(websocket, data)
                    elif message_type == 'wave_request':
                        await self.handle_wave_request(websocket, data)
                    elif message_type == 'currents_request':
                        await self.handle_currents_request(websocket, data)
                    elif message_type == 'chlorophyll_request':
                        await self.handle_chlorophyll_request(websocket, data)
                    elif message_type == 'ph_request':
                        await self.handle_ph_request(websocket, data)
                    elif message_type == 'microplastics_request':
                        await self.handle_microplastics_request(websocket, data)
                    elif message_type == 'biodiversity_request':
                        await self.handle_biodiversity_request(websocket, data)
                    elif message_type == 'coverage_request':
                        await self.handle_coverage_request(websocket, data)
                    elif message_type == 'ping':
                        await websocket.send(json.dumps({'type': 'pong'}))
                    else:
                        await self._send_error(websocket, f"Unknown message type: {message_type}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from client {client_id}: {e}")
                    await self._send_error(websocket, "Invalid JSON format")
                except Exception as e:
                    logger.error(f"Error processing message from client {client_id}: {e}")
                    await self._send_error(websocket, f"Message processing failed: {str(e)}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        finally:
            # Unregister client
            self.clients.remove(websocket)
            logger.info(f"Client {client_id} removed. Total clients: {len(self.clients)}")
    
    async def _send_error(self, websocket, message: str):
        """Send error message to client."""
        error_response = {
            'type': 'error',
            'payload': {
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
        }
        await websocket.send(json.dumps(error_response))
    
    async def _send_progress(self, websocket, message: str):
        """Send progress update to client."""
        progress_response = {
            'type': 'progress',
            'payload': {
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
        }
        await websocket.send(json.dumps(progress_response))
    
    async def broadcast_update(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        if self.clients:
            message_str = json.dumps(message, default=str)
            await asyncio.gather(
                *[client.send(message_str) for client in self.clients],
                return_exceptions=True
            )
    
    async def start(self):
        """Start the WebSocket server."""
        logger.info(f"Starting Climate Data WebSocket Server on port {self.port}...")
        
        async with websockets.serve(self.handle_client, "localhost", self.port):
            logger.info(f"Server running on ws://localhost:{self.port}")
            await asyncio.Future()  # Run forever

def main():
    """Run the WebSocket server."""
    # Get port from environment or use default
    port = int(os.getenv('WEBSOCKET_PORT', 8765))
    
    # Create and start server
    server = ClimateDataWebSocketServer(port=port)
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")

if __name__ == "__main__":
    main()