#!/usr/bin/env python3
"""
Base downloader class for ocean climate data.
Provides common functionality including date gap detection, status tracking, and error handling.
"""

import os
import json
import yaml
import requests
import logging
import shutil
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from abc import ABC, abstractmethod
import time

class BaseDataDownloader(ABC):
    """Base class for all data downloaders with common functionality."""
    
    def __init__(self, dataset_name: str, config_path: Optional[Path] = None):
        """
        Initialize base downloader.
        
        Args:
            dataset_name: Name of the dataset (sst, waves, currents, acidity, microplastics)
            config_path: Optional path to config directory
        """
        self.dataset_name = dataset_name
        self.config_path = config_path or Path(__file__).parent.parent / "config"
        
        # Load configuration
        self.config = self._load_config()
        self.dataset_config = self.config["datasets"][dataset_name]
        self.storage_config = self.config["storage"]
        self.download_config = self.config["download"]
        
        # Set up paths
        self.base_path = Path(self.storage_config["base_path"]).resolve()
        self.raw_data_path = self.base_path / self.storage_config["raw_data_path"] / dataset_name
        self.processed_data_path = self.base_path / self.storage_config["processed_data_path"]
        self.logs_path = self.base_path / self.storage_config["logs_path"]
        self.cache_path = self.base_path / self.storage_config["cache_path"]
        
        # Validate directory structure
        self._validate_directory_structure()
        
        # Create directories
        self.raw_data_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        self.logger = self._setup_logging()
        
        # Set up HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.download_config["user_agent"]
        })
        
        # Load credentials if required
        self.credentials = self._load_credentials() if self.dataset_config.get("credentials_required") else {}
        
        # Status tracking
        self.status_file = self.config_path / "status.json"
        
        self.logger.info(f"Initialized {dataset_name} downloader")
        
    def _validate_directory_structure(self) -> None:
        """Validate that the directory structure is correct."""
        # Basic validation - can be extended by subclasses
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration directory not found: {self.config_path}")
        
        # Check if storage base path parent exists
        if not self.base_path.parent.exists():
            raise FileNotFoundError(f"Storage parent directory not found: {self.base_path.parent}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from sources.yaml."""
        config_file = self.config_path / "sources.yaml"
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
            
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_credentials(self) -> Dict[str, str]:
        """Load credentials from environment or credentials.env file."""
        credentials = {}
        
        # Try to load from .env file
        env_file = self.config_path / "credentials.env"
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        credentials[key.strip()] = value.strip()
        
        # Override with environment variables
        for key in ['CMEMS_USERNAME', 'CMEMS_PASSWORD', 'NOAA_API_KEY']:
            if key in os.environ:
                credentials[key] = os.environ[key]
                
        return credentials
    
    def _validate_directory_structure(self):
        """Validate that directory paths follow expected structure."""
        # Ensure raw data path is under base_path/raw/{dataset}
        expected_raw_pattern = self.base_path / "raw" / self.dataset_name
        if self.raw_data_path != expected_raw_pattern:
            raise ValueError(
                f"Invalid raw data path structure: {self.raw_data_path}\n"
                f"Expected: {expected_raw_pattern}\n"
                f"Ensure dataset follows base_path/raw/{{dataset}} pattern"
            )
        
        # Warn about potential root-level dataset directories
        root_dataset_path = self.base_path / self.dataset_name
        if root_dataset_path.exists() and root_dataset_path != self.raw_data_path:
            print(f"⚠️  WARNING: Found dataset directory at root level: {root_dataset_path}")
            print(f"   This may cause data structure inconsistencies.")
            print(f"   Consider moving to: {self.raw_data_path}")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for this downloader."""
        logger = logging.getLogger(f"{self.dataset_name}_downloader")
        logger.setLevel(logging.INFO)
        
        # Create file handler
        log_file = self.logs_path / f"{self.dataset_name}_downloader.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        
        return logger
    
    def get_status(self) -> Dict[str, Any]:
        """Get current download status for this dataset."""
        if not self.status_file.exists():
            return {
                "last_date": None,
                "total_files": 0,
                "storage_gb": 0.0,
                "last_success": None,
                "last_error": None,
                "status": "not_started"
            }
        
        with open(self.status_file, 'r') as f:
            status = json.load(f)
            
        return status["datasets"].get(self.dataset_name, {
            "last_date": None,
            "total_files": 0,
            "storage_gb": 0.0,
            "last_success": None,
            "last_error": None,
            "status": "not_started"
        })
    
    def update_status(self, **kwargs):
        """Update status for this dataset."""
        # Load current status
        if self.status_file.exists():
            with open(self.status_file, 'r') as f:
                status = json.load(f)
        else:
            # Initialize status structure
            status = {
                "last_updated": None,
                "datasets": {},
                "system": {
                    "total_storage_gb": 0.0,
                    "available_storage_gb": None,
                    "last_health_check": None
                }
            }
        
        # Update dataset status
        if self.dataset_name not in status["datasets"]:
            status["datasets"][self.dataset_name] = {}
            
        status["datasets"][self.dataset_name].update(kwargs)
        status["last_updated"] = datetime.now().isoformat()
        
        # Write back to file
        with open(self.status_file, 'w') as f:
            json.dump(status, f, indent=2)
    
    def get_date_range_to_download(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[date]:
        """
        Calculate which dates need to be downloaded.
        
        Args:
            start_date: Optional start date override (YYYY-MM-DD)
            end_date: Optional end date override (YYYY-MM-DD)
            
        Returns:
            List of dates that need to be downloaded
        """
        current_status = self.get_status()
        
        # Determine start date
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        elif current_status["last_date"]:
            # Start from day after last successful download
            last_date = datetime.strptime(current_status["last_date"], "%Y-%m-%d").date()
            start = last_date + timedelta(days=1)
        else:
            # First time download - use test start date
            test_start = self.dataset_config["temporal_coverage"]["test_start"]
            start = datetime.strptime(test_start, "%Y-%m-%d").date()
        
        # Determine end date
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            # Download up to yesterday (today's data might not be available yet)
            end = date.today() - timedelta(days=1)
        
        # Generate date range
        dates_to_download = []
        current_date = start
        
        while current_date <= end:
            # Check if file already exists
            if not self._file_exists_for_date(current_date):
                dates_to_download.append(current_date)
            current_date += timedelta(days=1)
        
        self.logger.info(f"Found {len(dates_to_download)} dates to download from {start} to {end}")
        return dates_to_download
    
    def _file_exists_for_date(self, target_date: date) -> bool:
        """Check if data file exists for given date."""
        expected_path = self._get_file_path_for_date(target_date)
        return expected_path.exists()
    
    def _get_file_path_for_date(self, target_date: date) -> Path:
        """Get expected file path for a given date."""
        year_month = target_date.strftime("%Y/%m")
        filename = self._get_filename_for_date(target_date)
        return self.raw_data_path / year_month / filename
    
    @abstractmethod
    def _get_filename_for_date(self, target_date: date) -> str:
        """Get filename for a given date. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def download_date(self, target_date: date) -> bool:
        """Download data for a specific date. Must be implemented by subclasses."""
        pass
    
    def download_date_range(self, start_date: Optional[str] = None, end_date: Optional[str] = None, 
                          max_files: Optional[int] = None) -> Dict[str, Any]:
        """
        Download data for a range of dates.
        
        Args:
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            max_files: Optional limit on number of files to download
            
        Returns:
            Dictionary with download results
        """
        dates_to_download = self.get_date_range_to_download(start_date, end_date)
        
        if max_files and len(dates_to_download) > max_files:
            dates_to_download = dates_to_download[:max_files]
            self.logger.info(f"Limiting download to {max_files} files")
        
        if not dates_to_download:
            self.logger.info("No new dates to download")
            return {
                "success": True,
                "downloaded": 0,
                "skipped": 0,
                "failed": 0,
                "dates": []
            }
        
        # Update status to indicate download in progress
        self.update_status(status="downloading")
        
        results = {
            "success": True,
            "downloaded": 0,
            "skipped": 0,
            "failed": 0,
            "dates": [],
            "errors": []
        }
        
        for i, target_date in enumerate(dates_to_download):
            self.logger.info(f"Downloading {i+1}/{len(dates_to_download)}: {target_date}")
            
            try:
                success = self.download_date(target_date)
                if success:
                    results["downloaded"] += 1
                    results["dates"].append(target_date.strftime("%Y-%m-%d"))
                    
                    # Update status with latest successful date
                    self.update_status(
                        last_date=target_date.strftime("%Y-%m-%d"),
                        last_success=datetime.now().isoformat(),
                        status="active"
                    )
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                self.logger.error(f"Failed to download {target_date}: {e}")
                results["failed"] += 1
                results["errors"].append(f"{target_date}: {str(e)}")
                
                # Update status with error
                self.update_status(
                    last_error=f"{datetime.now().isoformat()}: {str(e)}",
                    status="error"
                )
            
            # Rate limiting
            if i < len(dates_to_download) - 1:  # Don't sleep after last download
                time.sleep(1)  # 1 second between downloads
        
        # Final status update
        if results["failed"] == 0:
            self.update_status(status="up_to_date")
        else:
            results["success"] = False
            
        self.logger.info(f"Download complete: {results['downloaded']} successful, {results['failed']} failed")
        return results
    
    def get_storage_usage(self) -> float:
        """Get storage usage in GB for this dataset."""
        total_bytes = 0
        
        for file_path in self.raw_data_path.rglob("*"):
            if file_path.is_file():
                total_bytes += file_path.stat().st_size
        
        return total_bytes / (1024 ** 3)  # Convert to GB
    
    def validate_downloaded_data(self) -> Dict[str, Any]:
        """Validate downloaded data integrity."""
        # This can be overridden by subclasses for dataset-specific validation
        files = list(self.raw_data_path.rglob("*"))
        data_files = [f for f in files if f.is_file() and not f.name.startswith('.')]
        
        return {
            "total_files": len(data_files),
            "storage_gb": self.get_storage_usage(),
            "validation_passed": True,
            "issues": []
        }
    
    def _auto_optimize_storage(self, target_date: date, raw_file_path: Path, 
                              intermediate_files: List[Path], final_file_path: Path) -> Dict[str, Any]:
        """
        Automatically optimize storage by removing raw and intermediate files after successful processing.
        
        Args:
            target_date: Date of the processed data
            raw_file_path: Path to the raw downloaded file
            intermediate_files: List of intermediate processing files to remove
            final_file_path: Path to the final processed file (kept)
            
        Returns:
            Dictionary with optimization results
        """
        optimization_log = {
            "timestamp": datetime.now().isoformat(),
            "date": target_date.strftime("%Y-%m-%d"),
            "files_removed": [],
            "space_freed_mb": 0,
            "final_file_size_kb": 0,
            "optimization_enabled": True,
            "errors": []
        }
        
        try:
            # Validate final file exists and is valid
            if not final_file_path.exists():
                optimization_log["errors"].append(f"Final file does not exist: {final_file_path}")
                optimization_log["optimization_enabled"] = False
                return optimization_log
            
            # Record final file size
            final_size_bytes = final_file_path.stat().st_size
            optimization_log["final_file_size_kb"] = round(final_size_bytes / 1024, 1)
            
            # Validate final file integrity (basic check)
            if final_size_bytes < 1024:  # Less than 1KB is suspicious
                optimization_log["errors"].append(f"Final file suspiciously small: {final_size_bytes} bytes")
                optimization_log["optimization_enabled"] = False
                return optimization_log
            
            # Remove raw file
            if raw_file_path.exists():
                raw_size = raw_file_path.stat().st_size
                raw_file_path.unlink()
                optimization_log["files_removed"].append({
                    "path": str(raw_file_path),
                    "size_mb": round(raw_size / (1024 * 1024), 3),
                    "type": "raw"
                })
                optimization_log["space_freed_mb"] += raw_size / (1024 * 1024)
                self.logger.info(f"Removed raw file: {raw_file_path} ({raw_size / (1024 * 1024):.1f} MB)")
            
            # Remove intermediate files
            for intermediate_file in intermediate_files:
                if intermediate_file.exists():
                    intermediate_size = intermediate_file.stat().st_size
                    intermediate_file.unlink()
                    optimization_log["files_removed"].append({
                        "path": str(intermediate_file),
                        "size_mb": round(intermediate_size / (1024 * 1024), 3),
                        "type": "intermediate"
                    })
                    optimization_log["space_freed_mb"] += intermediate_size / (1024 * 1024)
                    self.logger.info(f"Removed intermediate file: {intermediate_file} ({intermediate_size / (1024 * 1024):.1f} MB)")
            
            # Clean up empty directories
            self._cleanup_empty_directories(raw_file_path.parent)
            for intermediate_file in intermediate_files:
                self._cleanup_empty_directories(intermediate_file.parent)
            
            # Log optimization summary
            optimization_log["space_freed_mb"] = round(optimization_log["space_freed_mb"], 3)
            space_saved_percent = (optimization_log["space_freed_mb"] * 1024) / optimization_log["final_file_size_kb"] * 100
            
            self.logger.info(
                f"Storage optimization complete: {len(optimization_log['files_removed'])} files removed, "
                f"{optimization_log['space_freed_mb']:.1f} MB freed ({space_saved_percent:.1f}% reduction)"
            )
            
        except Exception as e:
            optimization_log["errors"].append(f"Optimization error: {str(e)}")
            self.logger.error(f"Storage optimization failed: {e}")
        
        return optimization_log
    
    def _cleanup_empty_directories(self, directory: Path):
        """Recursively remove empty directories."""
        try:
            if directory.exists() and directory.is_dir():
                # Remove directory if empty
                if not any(directory.iterdir()):
                    directory.rmdir()
                    self.logger.debug(f"Removed empty directory: {directory}")
                    # Recursively check parent directory
                    self._cleanup_empty_directories(directory.parent)
        except Exception as e:
            self.logger.debug(f"Could not remove directory {directory}: {e}")
    
    def _log_api_data_sample(self, target_date: date, final_file_path: Path) -> Dict[str, Any]:
        """
        Generate API data sample for development and testing.
        
        Args:
            target_date: Date of the data
            final_file_path: Path to the final processed file
            
        Returns:
            Dictionary with API sample data
        """
        api_sample = {
            "timestamp": datetime.now().isoformat(),
            "date": target_date.strftime("%Y-%m-%d"),
            "file_source": str(final_file_path),
            "file_size_kb": round(final_file_path.stat().st_size / 1024, 1),
            "sample_extractions": [],
            "data_structure": {},
            "api_readiness": {}
        }
        
        try:
            # Import here to avoid dependency issues
            import xarray as xr
            import numpy as np
            
            # Sample coordinates for testing
            test_coordinates = [
                {"name": "Equatorial Pacific", "lat": 0.0, "lon": 180.0},
                {"name": "North Atlantic", "lat": 45.0, "lon": -30.0},
                {"name": "Southern Ocean", "lat": -60.0, "lon": 0.0}
            ]
            
            with xr.open_dataset(final_file_path) as ds:
                # Document data structure
                api_sample["data_structure"] = {
                    "dimensions": dict(ds.dims),
                    "variables": list(ds.data_vars.keys()),
                    "coordinates": list(ds.coords.keys()),
                    "coordinate_ranges": {
                        "lat": {"min": float(ds.lat.min()), "max": float(ds.lat.max())},
                        "lon": {"min": float(ds.lon.min()), "max": float(ds.lon.max())}
                    },
                    "resolution": {
                        "lat": float(abs(ds.lat.diff('lat').mean())),
                        "lon": float(abs(ds.lon.diff('lon').mean()))
                    }
                }
                
                # Extract sample data points
                for coord in test_coordinates:
                    try:
                        start_time = time.time()
                        point_data = ds.sel(lat=coord["lat"], lon=coord["lon"], method='nearest')
                        extraction_time = (time.time() - start_time) * 1000
                        
                        sample_point = {
                            "location": coord["name"],
                            "requested_coordinates": {"lat": coord["lat"], "lon": coord["lon"]},
                            "actual_coordinates": {
                                "lat": float(point_data.lat.values),
                                "lon": float(point_data.lon.values)
                            },
                            "data": {},
                            "extraction_time_ms": round(extraction_time, 2)
                        }
                        
                        # Extract all variables
                        for var_name in point_data.data_vars:
                            var_data = point_data[var_name]
                            if var_data.size > 0:
                                value = float(var_data.values.flat[0]) if var_data.values.size > 0 else None
                                sample_point["data"][var_name] = {
                                    "value": value,
                                    "units": var_data.attrs.get("units", "unknown"),
                                    "long_name": var_data.attrs.get("long_name", var_name),
                                    "valid": not (np.isnan(value) if value is not None else True)
                                }
                        
                        api_sample["sample_extractions"].append(sample_point)
                        
                    except Exception as e:
                        api_sample["sample_extractions"].append({
                            "location": coord["name"],
                            "error": str(e)
                        })
                
                # API readiness assessment
                extraction_times = [s.get("extraction_time_ms", 1000) for s in api_sample["sample_extractions"] if "extraction_time_ms" in s]
                api_sample["api_readiness"] = {
                    "average_extraction_time_ms": round(np.mean(extraction_times), 2) if extraction_times else None,
                    "max_extraction_time_ms": round(max(extraction_times), 2) if extraction_times else None,
                    "performance_grade": "excellent" if all(t < 50 for t in extraction_times) else 
                                      "good" if all(t < 100 for t in extraction_times) else
                                      "needs_optimization",
                    "ready_for_api": all(t < 200 for t in extraction_times) if extraction_times else False
                }
        
        except ImportError:
            api_sample["error"] = "xarray not available for API sampling"
        except Exception as e:
            api_sample["error"] = f"API sampling failed: {str(e)}"
        
        # Save API sample log
        api_logs_path = self.logs_path / "api_samples"
        api_logs_path.mkdir(exist_ok=True)
        api_log_file = api_logs_path / f"{self.dataset_name}_api_sample_{target_date.strftime('%Y%m%d')}.json"
        
        with open(api_log_file, 'w') as f:
            json.dump(api_sample, f, indent=2, default=str)
        
        self.logger.info(f"API data sample logged: {api_log_file}")
        
        return api_sample