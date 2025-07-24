#!/usr/bin/env python3
"""
WebSocket Server for NOAA Climate Data Globe
Handles real-time communication between React frontend and Python backend.
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

from src.processors.enhanced_climate_data import EnhancedClimateDataProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NOAAWebSocketServer:
    def __init__(self):
        self.climate_processor = EnhancedClimateDataProcessor()
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
    
    async def broadcast_message(self, message):
        """Broadcast a message to all connected clients."""
        if self.clients:
            await asyncio.gather(
                *[self.send_message(client, message) for client in self.clients],
                return_exceptions=True
            )
    
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
            
            # Get climate data
            climate_data = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.get_climate_data_sync, 
                lat, lng
            )
            
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
    
    def get_climate_data_sync(self, lat, lng):
        """Synchronous wrapper for climate data collection."""
        try:
            # Use enhanced climate processor to get comprehensive data
            coord_str = f"{lat},{lng}"
            date_str = datetime.now().strftime("%Y-%m-%d")
            
            # Get enhanced climate data - use the correct method name
            if hasattr(self.climate_processor, 'process_enhanced_climate_data'):
                self.climate_processor.process_enhanced_climate_data(coord_str, date_str)
            elif hasattr(self.climate_processor, 'collect_enhanced_climate_data'):
                self.climate_processor.collect_enhanced_climate_data(coord_str, date_str)
            else:
                # Fallback: create simple climate data
                logger.warning("Climate processor method not found, creating fallback data")
                return self.create_fallback_data(lat, lng, date_str)
            
            # Read the generated CSV file
            cache_dir = Path("data/cache")
            if not cache_dir.exists():
                cache_dir.mkdir(parents=True, exist_ok=True)
            
            csv_files = list(cache_dir.glob(f"enhanced_climate_data_{lat}_{lng}_*.csv"))
            
            if csv_files:
                import pandas as pd
                df = pd.read_csv(csv_files[0])
                
                # Convert to list of dictionaries for JSON serialization
                climate_data = []
                for _, row in df.iterrows():
                    climate_data.append({
                        "latitude": row.get("latitude", lat),
                        "longitude": row.get("longitude", lng),
                        "date": row.get("date", date_str),
                        "data_source": row.get("data_source", "Unknown"),
                        "parameter": row.get("parameter", ""),
                        "value": row.get("value", 0),
                        "units": row.get("units", ""),
                        "description": row.get("description", ""),
                        "quality": row.get("quality", "U"),
                        "confidence": row.get("confidence", 0.5),
                        "climate_zone": row.get("climate_zone", "Unknown"),
                        "weather_labels": str(row.get("weather_labels", "")).split(",") if row.get("weather_labels") else [],
                        "timestamp": datetime.now().isoformat()
                    })
                
                return climate_data
            else:
                # Return fallback data if no CSV found
                return self.create_fallback_data(lat, lng, date_str)
                
        except Exception as e:
            logger.error(f"Error in climate data collection: {e}")
            return self.create_error_data(lat, lng, str(e))
    
    def create_fallback_data(self, lat, lng, date_str):
        """Create fallback climate data when no real data is available."""
        return [
            {
                "latitude": lat,
                "longitude": lng,
                "date": date_str,
                "data_source": "Synthetic_Fallback",
                "parameter": "sea_surface_temperature",
                "value": 20.5 + (lat / 90.0 * 10),  # Simple temperature estimate
                "units": "°C",
                "description": "Sea Surface Temperature (Estimated)",
                "quality": "F",
                "confidence": 0.3,
                "climate_zone": "Temperate" if abs(lat) < 30 else "Polar" if abs(lat) > 60 else "Subtropical",
                "weather_labels": ["marine"],
                "timestamp": datetime.now().isoformat()
            },
            {
                "latitude": lat,
                "longitude": lng,
                "date": date_str,
                "data_source": "Synthetic_Fallback",
                "parameter": "ocean_depth",
                "value": 2000,  # Average ocean depth
                "units": "m",
                "description": "Ocean Depth (Estimated)",
                "quality": "F",
                "confidence": 0.2,
                "climate_zone": "Marine",
                "weather_labels": ["oceanic"],
                "timestamp": datetime.now().isoformat()
            }
        ]
    
    def create_error_data(self, lat, lng, error_msg):
        """Create error data structure."""
        return [{
            "latitude": lat,
            "longitude": lng,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "data_source": "Error_Handler",
            "parameter": "system_error",
            "value": 0,
            "units": "",
            "description": f"System Error: {error_msg}",
            "quality": "E",
            "confidence": 0.0,
            "climate_zone": "Unknown",
            "weather_labels": ["error"],
            "timestamp": datetime.now().isoformat()
        }]
    
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
    server = NOAAWebSocketServer()
    
    logger.info("🌐 Starting NOAA WebSocket Server on ws://localhost:8765")
    
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
        sys.exit(1)