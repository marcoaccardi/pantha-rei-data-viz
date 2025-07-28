#!/usr/bin/env python3
"""
Ocean Data Management API

FastAPI application providing access to ocean climate data including:
- Sea Surface Temperature (SST)
- Ocean Waves
- Ocean Currents  
- Ocean Acidity/Biogeochemistry

All data is served from harmonized NetCDF files with unified coordinate systems.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
from pathlib import Path
import sys
from typing import Optional, List, Dict, Any
import logging
import asyncio

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.models.responses import (
    DatasetInfo, PointDataResponse, MultiDatasetResponse,
    HealthResponse, ErrorResponse
)
from api.endpoints.data_extractor import DataExtractor
from api.endpoints.texture_service import texture_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Ocean Data Management API",
    description="Access to harmonized ocean climate data including SST, waves, currents, and biogeochemistry",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize data extractor
data_extractor = DataExtractor()

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    logger.info("🌊 Ocean Data Management API starting up...")
    
    # Skip data availability check for faster startup
    logger.info("⚡ Fast startup mode - skipping data availability check")
    
    logger.info("✅ API ready to serve ocean data!")

@app.on_event("shutdown") 
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info("🌊 Ocean Data Management API shutting down...")

@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Ocean Data Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "datasets": "/datasets"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Fast health check - skip dataset scanning
        return HealthResponse(
            status="healthy",
            message="Ocean Data API is operational",
            datasets_available=["sst", "waves", "currents", "acidity", "microplastics"],
            total_files=19  # Known file count
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy", 
            message=f"Health check failed: {str(e)}",
            datasets_available=[],
            total_files=0
        )

@app.get("/datasets", response_model=Dict[str, DatasetInfo])
async def list_datasets():
    """List all available datasets with metadata."""
    try:
        return await data_extractor.get_available_datasets()
    except Exception as e:
        logger.error(f"Error listing datasets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/available-dates", response_model=Dict[str, List[str]])
async def get_available_dates():
    """Get all available dates for each dataset."""
    try:
        return await data_extractor.get_available_dates()
    except Exception as e:
        logger.error(f"Error getting available dates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sst/point", response_model=PointDataResponse)
async def get_sst_point(
    lat: float = Query(..., ge=-90, le=90, description="Latitude in degrees"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude in degrees"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (latest if not specified)")
):
    """Extract SST data at a specific point."""
    try:
        return await data_extractor.extract_point_data("sst", lat, lon, date)
    except Exception as e:
        logger.error(f"Error extracting SST data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/waves/point", response_model=PointDataResponse)
async def get_waves_point(
    lat: float = Query(..., ge=-90, le=90, description="Latitude in degrees"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude in degrees"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (latest if not specified)")
):
    """Extract wave data at a specific point."""
    try:
        return await data_extractor.extract_point_data("waves", lat, lon, date)
    except Exception as e:
        logger.error(f"Error extracting waves data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/currents/point", response_model=PointDataResponse)
async def get_currents_point(
    lat: float = Query(..., ge=-90, le=90, description="Latitude in degrees"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude in degrees"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (latest if not specified)")
):
    """Extract current data at a specific point."""
    try:
        return await data_extractor.extract_point_data("currents", lat, lon, date)
    except Exception as e:
        logger.error(f"Error extracting currents data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/acidity/point", response_model=PointDataResponse)
async def get_acidity_point(
    lat: float = Query(..., ge=-90, le=90, description="Latitude in degrees"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude in degrees"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (latest if not specified)")
):
    """Extract ocean acidity/biogeochemistry data at a specific point."""
    try:
        return await data_extractor.extract_point_data("acidity", lat, lon, date)
    except Exception as e:
        logger.error(f"Error extracting acidity data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/microplastics/point", response_model=PointDataResponse)
async def get_microplastics_point(
    lat: float = Query(..., ge=-90, le=90, description="Latitude in degrees"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude in degrees"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (nearest available if not specified)")
):
    """Extract microplastics data at a specific point. Includes real data (1993-2019) and synthetic predictions (2019-2025)."""
    try:
        return await data_extractor.extract_point_data("microplastics", lat, lon, date)
    except Exception as e:
        logger.error(f"Error extracting microplastics data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/microplastics/points")
async def get_microplastics_points(
    min_concentration: Optional[float] = Query(None, description="Minimum concentration filter"),
    data_source: Optional[str] = Query(None, description="Filter by data source: 'real' or 'synthetic'"),
    year_min: Optional[int] = Query(None, description="Minimum year filter"),
    year_max: Optional[int] = Query(None, description="Maximum year filter"),
    bounds: Optional[str] = Query(None, description="Spatial bounds as 'minLon,minLat,maxLon,maxLat'")
):
    """Get all microplastics measurement points for visualization overlay."""
    try:
        # Parse bounds if provided
        spatial_bounds = None
        if bounds:
            try:
                parts = bounds.split(',')
                if len(parts) == 4:
                    spatial_bounds = {
                        'min_lon': float(parts[0]),
                        'min_lat': float(parts[1]),
                        'max_lon': float(parts[2]),
                        'max_lat': float(parts[3])
                    }
            except:
                raise HTTPException(status_code=400, detail="Invalid bounds format. Use: minLon,minLat,maxLon,maxLat")
        
        # Get points from data extractor
        points = await data_extractor.get_all_microplastics_points(
            min_concentration=min_concentration,
            data_source=data_source,
            year_min=year_min,
            year_max=year_max,
            spatial_bounds=spatial_bounds
        )
        
        return points
    except Exception as e:
        logger.error(f"Error getting microplastics points: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/multi/point", response_model=MultiDatasetResponse)
async def get_multi_point(
    lat: float = Query(..., ge=-90, le=90, description="Latitude in degrees"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude in degrees"),
    datasets: str = Query("sst,waves,currents,acidity,microplastics", description="Comma-separated list of datasets"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (latest if not specified)")
):
    """Extract data from multiple datasets at a specific point."""
    try:
        dataset_list = [d.strip() for d in datasets.split(",")]
        logger.info(f"🌊 Multi-point request for {dataset_list} at ({lat}, {lon}) on {date}")
        
        # Add overall timeout for the entire request
        result = await asyncio.wait_for(
            data_extractor.extract_multi_point_data(dataset_list, lat, lon, date),
            timeout=60.0  # 60 second total timeout
        )
        
        logger.info(f"✅ Multi-point request completed successfully")
        return result
    except asyncio.TimeoutError:
        logger.error(f"⏰ Multi-point request timed out after 60 seconds")
        raise HTTPException(status_code=504, detail="Request timed out")
    except Exception as e:
        logger.error(f"❌ Error extracting multi-dataset data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Texture Endpoints

@app.get("/textures/earth/nasa_world_topo_bathy.jpg")
async def get_earth_texture():
    """Serve the NASA Earth texture file."""
    earth_texture_path = Path(__file__).parent.parent.parent / "ocean-data" / "textures" / "earth" / "nasa_world_topo_bathy.jpg"
    
    if not earth_texture_path.exists():
        logger.error(f"Earth texture not found at: {earth_texture_path}")
        raise HTTPException(status_code=404, detail="Earth texture not found")
    
    return FileResponse(
        path=str(earth_texture_path),
        media_type="image/jpeg",
        filename="nasa_world_topo_bathy.jpg"
    )

@app.get("/textures/{category}")
async def get_texture(
    category: str,
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (latest if not specified)"),
    resolution: str = Query("medium", description="Texture resolution: preview, low, medium, high")
):
    """Serve texture image for specified category, date, and resolution."""
    try:
        return texture_service.serve_texture(category, date, resolution)
    except Exception as e:
        logger.error(f"Error serving texture: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/textures/list/{category}")
async def list_category_textures(category: str):
    """List all available textures for a specific category."""
    try:
        available = texture_service.get_available_textures()
        if category not in available:
            raise HTTPException(status_code=404, detail=f"Category not found: {category}")
        
        return {
            "category": category,
            "available_dates": list(available[category].keys()),
            "textures": available[category]
        }
    except Exception as e:
        logger.error(f"Error listing textures for category {category}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/textures/metadata")
async def get_texture_metadata():
    """Get metadata and summary of all available textures."""
    try:
        return {
            "available_textures": texture_service.get_available_textures(),
            "summary": texture_service.get_texture_summary()
        }
    except Exception as e:
        logger.error(f"Error getting texture metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            status_code=exc.status_code
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            status_code=500
        ).dict()
    )

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )