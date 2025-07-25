#!/usr/bin/env python3
"""
Fallback WebSocket server for ocean climate data streaming.
Provides mock data when full backend dependencies are not available.
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
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FallbackWebSocketServer:
    """Fallback WebSocket server with mock ocean data."""
    
    def __init__(self, port: int = 8765):
        """Initialize the fallback WebSocket server."""
        self.port = port
        self.clients = set()
        logger.info("Fallback WebSocket Server initialized")
    
    def generate_mock_ocean_data(self, lat: float, lon: float, date: str) -> Dict[str, Any]:
        """Generate realistic mock ocean data based on coordinates and date."""
        
        # Generate realistic temperature based on latitude and season
        base_temp = 15 + (30 - abs(lat)) * 0.5  # Warmer near equator
        seasonal_adjustment = 2 * (datetime.now().month - 6) / 12  # Seasonal variation
        temperature = base_temp + seasonal_adjustment + random.uniform(-2, 2)
        
        # Generate other realistic parameters based on location
        salinity = 34.0 + random.uniform(-1.5, 1.5)  # Typical ocean salinity
        wave_height = random.uniform(0.5, 4.0)
        current_speed = random.uniform(0.1, 0.8)
        current_direction = random.uniform(0, 360)
        chlorophyll = random.uniform(0.1, 2.5)
        ph = 8.1 + random.uniform(-0.3, 0.2)
        
        return {
            'status': 'success',
            'data': [
                {
                    'parameter': 'sea_surface_temperature',
                    'value': round(temperature, 2),
                    'units': '°C',
                    'description': 'Sea Surface Temperature',
                    'quality': 'Synthetic',
                    'confidence': 0.85,
                    'zone': 'Ocean',
                    'source': 'Fallback_Ocean_Model'
                },
                {
                    'parameter': 'salinity',
                    'value': round(salinity, 2),
                    'units': 'PSU',
                    'description': 'Ocean Salinity',
                    'quality': 'Synthetic',
                    'confidence': 0.80,
                    'zone': 'Ocean',
                    'source': 'Fallback_Ocean_Model'
                },
                {
                    'parameter': 'significant_wave_height',
                    'value': round(wave_height, 2),
                    'units': 'm',
                    'description': 'Significant Wave Height',
                    'quality': 'Synthetic',
                    'confidence': 0.75,
                    'zone': 'Ocean',
                    'source': 'Fallback_Wave_Model'
                },
                {
                    'parameter': 'ocean_current_speed',
                    'value': round(current_speed, 2),
                    'units': 'm/s',
                    'description': 'Ocean Current Speed',
                    'quality': 'Synthetic',
                    'confidence': 0.70,
                    'zone': 'Ocean',
                    'source': 'Fallback_Current_Model'
                },
                {
                    'parameter': 'ocean_current_direction',
                    'value': round(current_direction, 1),
                    'units': 'degrees',
                    'description': 'Ocean Current Direction',
                    'quality': 'Synthetic',
                    'confidence': 0.70,
                    'zone': 'Ocean',
                    'source': 'Fallback_Current_Model'
                },
                {
                    'parameter': 'chlorophyll_a_concentration',
                    'value': round(chlorophyll, 3),
                    'units': 'mg/m³',
                    'description': 'Chlorophyll-a Concentration',
                    'quality': 'Synthetic',
                    'confidence': 0.65,
                    'zone': 'Ocean',
                    'source': 'Fallback_Bio_Model'
                },
                {
                    'parameter': 'ocean_ph',
                    'value': round(ph, 2),
                    'units': 'pH units',
                    'description': 'Ocean pH Level',
                    'quality': 'Synthetic',
                    'confidence': 0.75,
                    'zone': 'Ocean',
                    'source': 'Fallback_Chemistry_Model'
                }
            ],
            'metadata': {
                'coordinates': {'lat': lat, 'lon': lon},
                'date': date,
                'data_source': 'Fallback Ocean Model',
                'note': 'This is synthetic data for demonstration purposes'
            }
        }
    
    def validate_ocean_point(self, lat: float, lon: float) -> bool:
        """Simple ocean validation - assume most points are valid."""
        # Basic validation - exclude obvious land masses
        if lat is None or lon is None:
            return False
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return False
        
        # For demo purposes, assume most coordinates are ocean
        # In reality, this would use proper land/ocean detection
        return True
    
    async def handle_temperature_request(self, websocket, message: Dict[str, Any]):
        """Handle temperature data requests with mock data."""
        try:
            logger.info("🌊 Processing temperature request (fallback mode)")
            
            # Extract coordinates from payload
            payload = message.get('payload', {})
            coordinates = payload.get('coordinates', {})
            lat = coordinates.get('lat')
            lon = coordinates.get('lon')
            
            if not self.validate_ocean_point(lat, lon):
                await self._send_error(websocket, "Invalid ocean coordinates")
                return
            
            # Extract date range
            date_range = payload.get('dateRange', {})
            start_date = date_range.get('start', '2024-01-01')
            
            logger.info(f"📍 Generating mock data for {lat:.2f}, {lon:.2f} on {start_date}")
            
            # Generate mock data
            mock_data = self.generate_mock_ocean_data(lat, lon, start_date)
            
            # Format response for frontend
            response = {
                'type': 'temperature_data',
                'coordinates': {'lat': lat, 'lon': lon},
                'data': mock_data,
                'cached': False,
                'timestamp': datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(response, default=str))
            logger.info(f"✅ Sent mock temperature data for {lat:.2f}, {lon:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Error handling temperature request: {e}")
            await self._send_error(websocket, f"Temperature data query failed: {str(e)}")
    
    async def handle_client(self, websocket, path):
        """Handle WebSocket client connections."""
        # Register client
        self.clients.add(websocket)
        client_id = id(websocket)
        logger.info(f"🔗 Client {client_id} connected. Total clients: {len(self.clients)}")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type')
                    
                    logger.info(f"📨 Received message type: {message_type} from client {client_id}")
                    
                    if message_type == 'temperature_request':
                        await self.handle_temperature_request(websocket, data)
                    elif message_type in ['salinity_request', 'wave_request', 'currents_request', 
                                        'chlorophyll_request', 'ph_request', 'biodiversity_request', 
                                        'microplastics_request']:
                        # Handle other request types with the same mock data approach
                        await self.handle_temperature_request(websocket, data)
                    elif message_type == 'ping':
                        await websocket.send(json.dumps({'type': 'pong'}))
                    else:
                        logger.warning(f"⚠️ Unknown message type: {message_type}")
                        await self._send_error(websocket, f"Unknown message type: {message_type}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON from client {client_id}: {e}")
                    await self._send_error(websocket, "Invalid JSON format")
                except Exception as e:
                    logger.error(f"❌ Error processing message from client {client_id}: {e}")
                    await self._send_error(websocket, f"Message processing failed: {str(e)}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 Client {client_id} disconnected")
        finally:
            # Unregister client
            self.clients.remove(websocket)
            logger.info(f"👋 Client {client_id} removed. Total clients: {len(self.clients)}")
    
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
    
    async def start(self):
        """Start the fallback WebSocket server."""
        logger.info(f"🚀 Starting Fallback WebSocket Server on port {self.port}...")
        logger.info("⚠️ This server provides MOCK DATA for demonstration purposes")
        
        async with websockets.serve(self.handle_client, "localhost", self.port):
            logger.info(f"✅ Fallback server running on ws://localhost:{self.port}")
            await asyncio.Future()  # Run forever

def main():
    """Run the fallback WebSocket server."""
    # Get port from environment or use default
    port = int(os.getenv('WEBSOCKET_PORT', 8765))
    
    # Create and start server
    server = FallbackWebSocketServer(port=port)
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("🛑 Fallback server stopped by user")

if __name__ == "__main__":
    main()