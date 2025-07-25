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
from fastapi.responses import JSONResponse
import uvicorn
from pathlib import Path
import sys
from typing import Optional, List, Dict, Any
import logging

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.models.responses import (
    DatasetInfo, PointDataResponse, MultiDatasetResponse,
    HealthResponse, ErrorResponse
)
from api.endpoints.data_extractor import DataExtractor

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
    
    # Verify data availability
    available_datasets = await data_extractor.get_available_datasets()
    logger.info(f"📊 Available datasets: {list(available_datasets.keys())}")
    
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
        available_datasets = await data_extractor.get_available_datasets()
        total_files = sum(info.file_count for info in available_datasets.values())
        
        return HealthResponse(
            status="healthy",
            message="Ocean Data API is operational",
            datasets_available=list(available_datasets.keys()),
            total_files=total_files
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

@app.get("/multi/point", response_model=MultiDatasetResponse)
async def get_multi_point(
    lat: float = Query(..., ge=-90, le=90, description="Latitude in degrees"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude in degrees"),
    datasets: str = Query("sst,waves,currents,acidity", description="Comma-separated list of datasets"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (latest if not specified)")
):
    """Extract data from multiple datasets at a specific point."""
    try:
        dataset_list = [d.strip() for d in datasets.split(",")]
        return await data_extractor.extract_multi_point_data(dataset_list, lat, lon, date)
    except Exception as e:
        logger.error(f"Error extracting multi-dataset data: {e}")
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