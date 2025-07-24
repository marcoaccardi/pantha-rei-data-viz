#!/usr/bin/env python3
"""
Simple WebSocket Server for NOAA Climate Data Globe
Direct fallback data generation without complex dependencies.
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleNOAAWebSocketServer:
    def __init__(self):
        self.clients = set()
        
    async def register_client(self, websocket):
        """Register a new client connection."""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
        
        # Send connection confirmation
        await self.send_message(websocket, {
            "type": "connection",
            "payload": {
                "message": "Connected to NOAA WebSocket server",
                "timestamp": datetime.now().isoformat()
            }
        })
    
    async def unregister_client(self, websocket):
        """Unregister a client connection."""
        self.clients.discard(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
    
    async def send_message(self, websocket, message):
        """Send a message to a specific client."""
        try:
            await websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            await self.unregister_client(websocket)
    
    async def handle_coordinate_request(self, websocket, payload):
        """Handle coordinate data request from frontend."""
        try:
            coordinates = payload.get("coordinates", {})
            lat = coordinates.get("lat", 0.0)
            lng = coordinates.get("lng", 0.0)
            
            logger.info(f"Processing climate data request for: {lat}, {lng}")
            
            # Send progress update
            await self.send_message(websocket, {
                "type": "progress",
                "payload": {
                    "message": f"Fetching climate data for {lat:.4f}, {lng:.4f}...",
                    "timestamp": datetime.now().isoformat()
                }
            })
            
            # Generate synthetic climate data
            climate_data = self.generate_synthetic_climate_data(lat, lng)
            
            # Send climate data response
            await self.send_message(websocket, {
                "type": "climate_data",
                "payload": {
                    "coordinates": coordinates,
                    "climateData": climate_data,
                    "timestamp": datetime.now().isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"Error processing coordinate request: {e}")
            await self.send_message(websocket, {
                "type": "error",
                "payload": {
                    "message": f"Error fetching climate data: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
            })
    
    def generate_synthetic_climate_data(self, lat, lng):
        """Generate realistic synthetic climate data based on coordinates."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Calculate realistic values based on latitude
        base_temp = 25 - abs(lat) * 0.6  # Warmer at equator, colder at poles
        is_ocean = abs(lat) < 70  # Assume ocean if not polar
        
        climate_data = []
        
        # Sea Surface Temperature
        if is_ocean:
            sst = base_temp + random.uniform(-3, 3)
            climate_data.append({
                "latitude": lat,
                "longitude": lng,
                "date": date_str,
                "data_source": "Synthetic_Ocean_Model",
                "parameter": "sea_surface_temperature",
                "value": round(sst, 2),
                "units": "°C",
                "description": "Sea Surface Temperature",
                "quality": "S",  # Synthetic
                "confidence": 0.7,
                "climate_zone": self.get_climate_zone(lat),
                "weather_labels": ["oceanic", "marine"],
                "timestamp": datetime.now().isoformat()
            })
        
        # Ocean Depth
        depth = random.uniform(1000, 4000) if is_ocean else 0
        climate_data.append({
            "latitude": lat,
            "longitude": lng,
            "date": date_str,
            "data_source": "Bathymetry_Model",
            "parameter": "ocean_depth",
            "value": round(depth, 0),
            "units": "m",
            "description": "Ocean Depth",
            "quality": "S",
            "confidence": 0.5,
            "climate_zone": "Marine" if is_ocean else "Terrestrial",
            "weather_labels": ["bathymetry"],
            "timestamp": datetime.now().isoformat()
        })
        
        # Salinity
        if is_ocean:
            salinity = 35 + random.uniform(-2, 2)  # Typical ocean salinity
            climate_data.append({
                "latitude": lat,
                "longitude": lng,
                "date": date_str,
                "data_source": "Ocean_Chemistry_Model",
                "parameter": "salinity",
                "value": round(salinity, 2),
                "units": "PSU",
                "description": "Ocean Salinity",
                "quality": "S",
                "confidence": 0.6,
                "climate_zone": self.get_climate_zone(lat),
                "weather_labels": ["chemistry", "salinity"],
                "timestamp": datetime.now().isoformat()
            })
        
        # pH Level
        if is_ocean:
            ph = 8.1 + random.uniform(-0.3, 0.1)  # Ocean pH slightly basic
            climate_data.append({
                "latitude": lat,
                "longitude": lng,
                "date": date_str,
                "data_source": "Ocean_Chemistry_Model",
                "parameter": "ph_level",
                "value": round(ph, 2),
                "units": "pH",
                "description": "Ocean pH Level",
                "quality": "S",
                "confidence": 0.6,
                "climate_zone": self.get_climate_zone(lat),
                "weather_labels": ["chemistry", "acidity"],
                "timestamp": datetime.now().isoformat()
            })
        
        # Chlorophyll-a (marine productivity)
        if is_ocean:
            chlorophyll = random.uniform(0.1, 2.5)  # mg/m³
            climate_data.append({
                "latitude": lat,
                "longitude": lng,
                "date": date_str,
                "data_source": "Marine_Biology_Model",
                "parameter": "chlorophyll_a",
                "value": round(chlorophyll, 2),
                "units": "mg/m³",
                "description": "Chlorophyll-a Concentration",
                "quality": "S",
                "confidence": 0.5,
                "climate_zone": self.get_climate_zone(lat),
                "weather_labels": ["biology", "productivity"],
                "timestamp": datetime.now().isoformat()
            })
        
        return climate_data
    
    def get_climate_zone(self, lat):
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
    
    async def handle_message(self, websocket, message):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            payload = data.get("payload", {})
            
            if message_type == "coordinate_data":
                await self.handle_coordinate_request(websocket, payload)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
            await self.send_message(websocket, {
                "type": "error",
                "payload": {
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                }
            })
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def handle_client(self, websocket, path):
        """Handle individual client connection."""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)

async def main():
    """Start the WebSocket server."""
    server = SimpleNOAAWebSocketServer()
    
    logger.info("🌐 Starting Simple NOAA WebSocket Server on ws://localhost:8765")
    
    # Start WebSocket server with updated signature for websockets v12+
    async def handler(websocket):
        await server.handle_client(websocket, None)
    
    start_server = websockets.serve(
        handler,
        "localhost",
        8765,
        ping_interval=20,
        ping_timeout=10
    )
    
    await start_server
    logger.info("✅ WebSocket server started successfully")
    logger.info("🌍 Ready to receive globe coordinate requests")
    
    # Keep server running
    await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 WebSocket server stopped")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        import sys
        sys.exit(1)