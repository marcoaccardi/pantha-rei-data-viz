#!/usr/bin/env python3
"""
Current acidity downloader for CMEMS Global Ocean Biogeochemistry Analysis and Forecast (2021-present).
Downloads daily NetCDF files from Copernicus Marine Environment Monitoring Service.
"""

import os
from pathlib import Path
from typing import Optional, Union, Dict, Any
from datetime import date, datetime

from .acidity_downloader import AcidityDownloader

class AcidityCurrentDownloader(AcidityDownloader):
    """Downloads current/forecast acidity data from CMEMS (2021-present)."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize Current Acidity downloader."""
        # Initialize base downloader with specific dataset name
        from .base_downloader import BaseDataDownloader
        BaseDataDownloader.__init__(self, "acidity_current", config_path)
        
        # Load acidity_current specific configuration
        self.dataset_name = "acidity_current"
        self.dataset_config = self.config["datasets"][self.dataset_name]
        
        # Acidity-specific configuration
        self.product_id = self.dataset_config["product_id"]
        self.dataset_id = self.dataset_config["dataset_id"]
        self.base_url = self.dataset_config["base_url"]
        self.spatial_resolution = self.dataset_config["spatial_resolution"]
        self.variables = self.dataset_config["variables"]
        self.layers = self.dataset_config.get("layers", ["surface"])
        
        # Processing configuration
        self.needs_coord_harmonization = self.dataset_config["processing"]["harmonize_coords"]
        
        # Update paths for current data
        self.raw_data_path = self.raw_data_path.parent / "acidity_current"
        self.raw_data_path.mkdir(parents=True, exist_ok=True)
        
        # Create processed data directories if needed
        if self.needs_coord_harmonization:
            self.harmonized_path = self.processed_data_path / "unified_coords" / "acidity_current"
            self.harmonized_path.mkdir(parents=True, exist_ok=True)
        
        # Load credentials from parent class logic
        env_file = self.config_path / ".env"
        self.cmems_username = None
        self.cmems_password = None
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        if key.strip() == 'CMEMS_USERNAME':
                            self.cmems_username = value.strip()
                        elif key.strip() == 'CMEMS_PASSWORD':
                            self.cmems_password = value.strip()
        
        # Also check environment variables as fallback
        if not self.cmems_username:
            self.cmems_username = os.getenv("CMEMS_USERNAME")
        if not self.cmems_password:
            self.cmems_password = os.getenv("CMEMS_PASSWORD")
        
        # Validate CMEMS credentials
        if not self.cmems_username or not self.cmems_password:
            raise ValueError("CMEMS credentials not found. Please configure CMEMS_USERNAME and CMEMS_PASSWORD in .env file")
        
        self.logger.info(f"Initialized Current Acidity downloader for CMEMS product: {self.product_id}")
    
    # Import methods from parent AcidityDownloader
    def download_date(self, target_date: date) -> bool:
        """Download current acidity data for a specific date."""
        return super().download_date(target_date)
    
    def _validate_netcdf_file(self, file_path: Path) -> bool:
        """Validate NetCDF file using parent method."""
        return super()._validate_netcdf_file(file_path)
    
    def _process_downloaded_file(self, raw_file_path: Path, target_date: date) -> bool:
        """Process downloaded file using parent method."""
        return super()._process_downloaded_file(raw_file_path, target_date)
    
    def _get_filename_for_date(self, target_date: date) -> str:
        """Get filename for current acidity file for given date."""
        return f"acidity_current_{target_date.strftime('%Y%m%d')}.nc"
    
    def validate_date_range(self, start_date: date, end_date: date) -> tuple[date, date]:
        """
        Validate and adjust date range for current dataset.
        
        Args:
            start_date: Requested start date
            end_date: Requested end date
            
        Returns:
            Tuple of (validated_start_date, validated_end_date)
        """
        # Current dataset boundaries
        dataset_start = date(2021, 10, 1)
        # For current dataset, end date is "present" - use today as end
        dataset_end = date.today()
        
        # Adjust dates to fit within current dataset bounds
        validated_start = max(start_date, dataset_start)
        validated_end = min(end_date, dataset_end)
        
        if validated_start > dataset_end or validated_end < dataset_start:
            raise ValueError(
                f"Date range {start_date} to {end_date} is outside current dataset range "
                f"({dataset_start} to {dataset_end})"
            )
        
        if validated_start != start_date or validated_end != end_date:
            self.logger.info(
                f"Adjusted date range from {start_date}-{end_date} to {validated_start}-{validated_end} "
                f"to fit current dataset bounds"
            )
        
        return validated_start, validated_end
    
    def _log_api_data_sample(self, target_date: date, processed_file: Path) -> dict:
        """Override to use current-specific sample filename."""
        try:
            # Use parent method but override the sample filename
            api_sample_data = super()._log_api_data_sample(target_date, processed_file)
            
            # Update the sample file name to indicate current source
            api_sample_dir = self.logs_path / "api_samples"
            api_sample_dir.mkdir(parents=True, exist_ok=True)
            
            sample_filename = f"acidity_current_api_sample_{target_date.strftime('%Y%m%d')}.json"
            sample_file = api_sample_dir / sample_filename
            
            # Update dataset name in the sample data
            api_sample_data["dataset"] = "acidity_current"
            api_sample_data["source"] = f"{self.product_id} (Current/Forecast)"
            
            # Save the updated sample
            import json
            with open(sample_file, 'w') as f:
                json.dump(api_sample_data, f, indent=2)
            
            self.logger.info(f"Current API sample data generated: {sample_file}")
            return api_sample_data
            
        except Exception as e:
            self.logger.error(f"Error generating current API sample: {e}")
            return {"api_readiness": {"ready_for_api": False}}
    
    def download_date_range(self, start_date: Union[str, date], end_date: Union[str, date], max_files: Optional[int] = None) -> Dict[str, Any]:
        """
        Download current acidity data for a date range.
        
        Args:
            start_date: Start date (string or date object)
            end_date: End date (string or date object)
            max_files: Maximum number of files to download
            
        Returns:
            Dictionary with download results
        """
        # Convert string dates to date objects if needed
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
        # Call parent class method with date objects
        return super().download_date_range(start_date, end_date, max_files)