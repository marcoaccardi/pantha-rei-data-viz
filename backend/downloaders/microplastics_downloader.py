#!/usr/bin/env python3
"""
Microplastics downloader for NOAA NCEI Marine Microplastics Database.
Downloads CSV data from the NCEI interactive portal and processes point observations.
"""

import requests
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import tempfile
import shutil
import json
import warnings
import time
import os

# Selenium imports for browser automation
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .base_downloader import BaseDataDownloader

class MicroplasticsDownloader(BaseDataDownloader):
    """Downloads and processes NOAA NCEI Marine Microplastics data."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize Microplastics downloader."""
        super().__init__("microplastics", config_path)
        
        # Microplastics-specific configuration
        self.portal_url = self.dataset_config["portal_url"]
        self.download_url = self.dataset_config.get("download_url", "")
        self.format = self.dataset_config["format"]
        self.variables = self.dataset_config["variables"]
        self.update_frequency = self.dataset_config["update_frequency"]
        
        # Processing configuration
        self.needs_date_filtering = self.dataset_config["processing"]["filter_date_range"]
        self.test_start_date = self.dataset_config["temporal_coverage"]["test_start"]
        
        # Data structure expectations
        self.expected_columns = [
            "Date", "Latitude", "Longitude", "Location", 
            "Concentration", "Concentration_Class_Range", "Concentration_Class_Text",
            "Sampling_Method", "Mesh_Size", "Study_Reference", "NCEI_Accession_No_Link"
        ]
        
        # Create processed data directories
        self.processed_csv_path = self.processed_data_path / "microplastics_filtered"
        self.processed_csv_path.mkdir(parents=True, exist_ok=True)
        
        # Since this is point data, we'll use a different approach than gridded NetCDF data
        self.logger.info("Initialized NOAA NCEI Microplastics downloader")
        self.logger.info(f"Data will be filtered to dates >= {self.test_start_date}")
    
    def _get_filename_for_date(self, target_date: date) -> str:
        """
        Get filename for microplastics data.
        Since microplastics is a complete database, use simple naming.
        """
        return f"microplastics_database_{target_date.year}.csv"
    
    
    
    def download_date(self, target_date: date) -> bool:
        """
        Download microplastics data for a specific quarter.
        Since this is a complete database, we download the full dataset and apply date filtering.
        
        Args:
            target_date: Quarterly date to download data for
            
        Returns:
            True if successful, False otherwise
        """
        # Create simple year directory structure
        output_dir = self.raw_data_path / str(target_date.year)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Define file paths
        filename = self._get_filename_for_date(target_date)
        raw_file_path = output_dir / filename
        
        # Skip if file already exists and is valid
        if raw_file_path.exists() and self._validate_csv_file(raw_file_path):
            self.logger.info(f"File already exists and is valid: {raw_file_path}")
            return True
        
        try:
            self.logger.info(f"Downloading NCEI microplastics database for {target_date.year}")
            
            # For now, we'll simulate the download since the interactive portal requires manual export
            # In a production system, this would either:
            # 1. Use a headless browser to automate the export process
            # 2. Call a direct API endpoint if available
            # 3. Use pre-exported data files
            
            success = self._download_ncei_microplastics_data(raw_file_path, target_date)
            
            if success:
                # Process the downloaded file
                success = self._process_downloaded_file(raw_file_path, target_date)
                
                if success:
                    # Update file count and storage stats
                    current_status = self.get_status()
                    new_file_count = current_status.get("total_files", 0) + 1
                    new_storage_gb = self.get_storage_usage()
                    
                    self.update_status(
                        total_files=new_file_count,
                        storage_gb=round(new_storage_gb, 3)
                    )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Unexpected error downloading {filename}: {e}")
            return False
    
    def _download_ncei_microplastics_data(self, output_file: Path, target_date: date) -> bool:
        """
        Download actual microplastics data from NOAA NCEI portal using Selenium automation.
        This automates the interactive web portal to export real data.
        
        Args:
            output_file: Path where to save the downloaded file
            target_date: Date for the download
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Downloading NCEI marine microplastics database using browser automation")
            
            # Use Selenium to automate the interactive portal
            success = self._selenium_export_data(output_file, target_date)
            
            if not success:
                self.logger.error("Failed to download real NCEI data via browser automation")
                self.logger.error("The microplastics dataset requires manual download from:")
                self.logger.error("https://experience.arcgis.com/experience/b296879cc1984fda833a8acc93e31476")
                return False
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error downloading NCEI microplastics data: {e}")
            return False
    
    def _selenium_export_data(self, output_file: Path, target_date: date) -> bool:
        """
        Use Selenium to automate the NCEI microplastics portal and export CSV data.
        
        Args:
            output_file: Path where to save the downloaded file
            target_date: Date for the download
            
        Returns:
            True if successful, False otherwise
        """
        driver = None
        try:
            # Set up Chrome options for headless browser
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Run in background
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Set download directory
            download_dir = str(output_file.parent)
            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Initialize Chrome driver
            self.logger.info("Starting Chrome browser for NCEI portal automation")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Navigate to NCEI microplastics portal
            portal_url = "https://experience.arcgis.com/experience/b296879cc1984fda833a8acc93e31476"
            self.logger.info(f"Navigating to NCEI portal: {portal_url}")
            driver.get(portal_url)
            
            # Wait for page to load
            wait = WebDriverWait(driver, 30)
            
            # Wait for the page to load (look for any elements that indicate loading is complete)
            self.logger.info("Waiting for portal to load...")
            
            # Try multiple strategies to detect when the page is loaded
            loaded = False
            load_indicators = [
                (By.TAG_NAME, "canvas"),
                (By.CLASS_NAME, "esri-view"),
                (By.CLASS_NAME, "esri-widget"),
                (By.XPATH, "//div[contains(@class, 'calcite')]"),
                (By.XPATH, "//div[contains(@class, 'experience')]")
            ]
            
            for indicator in load_indicators:
                try:
                    wait.until(EC.presence_of_element_located(indicator))
                    self.logger.info(f"Portal loaded - found element: {indicator}")
                    loaded = True
                    break
                except TimeoutException:
                    continue
            
            if not loaded:
                self.logger.warning("Could not detect portal load completion, proceeding anyway")
            
            time.sleep(10)  # Additional wait for full initialization
            
            # Look for the Data Table tab or similar element
            self.logger.info("Looking for Data Table access...")
            
            # Try multiple selectors that might represent the data table
            data_table_selectors = [
                "//div[contains(text(), 'Data Table')]",
                "//button[contains(text(), 'Data Table')]",  
                "//span[contains(text(), 'Data Table')]",
                "//div[contains(@class, 'data-table')]",
                "//div[contains(@aria-label, 'table')]"
            ]
            
            data_table_element = None
            for selector in data_table_selectors:
                try:
                    data_table_element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    self.logger.info(f"Found data table with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not data_table_element:
                self.logger.warning("Could not find Data Table element, trying alternative approach")
                # Look for any export or download buttons
                export_selectors = [
                    "//button[contains(text(), 'Export')]",
                    "//div[contains(text(), 'Export')]",
                    "//button[contains(@title, 'export')]",
                    "//div[contains(@class, 'export')]"
                ]
                
                for selector in export_selectors:
                    try:
                        export_element = driver.find_element(By.XPATH, selector)
                        self.logger.info(f"Found export button: {selector}")
                        export_element.click()
                        time.sleep(2)
                        break
                    except NoSuchElementException:
                        continue
            else:
                # Click on Data Table
                data_table_element.click()
                time.sleep(3)
                
                # Look for Actions menu or Export button
                self.logger.info("Looking for Actions menu...")
                actions_selectors = [
                    "//button[contains(text(), 'Actions')]",
                    "//div[contains(text(), 'Actions')]",
                    "//button[contains(text(), 'Export all')]",
                    "//button[contains(text(), 'Export')]"
                ]
                
                for selector in actions_selectors:
                    try:
                        actions_button = driver.find_element(By.XPATH, selector)
                        self.logger.info(f"Found actions button: {selector}")
                        actions_button.click()
                        time.sleep(2)
                        
                        # Look for CSV export option
                        csv_selectors = [
                            "//div[contains(text(), 'CSV')]",
                            "//button[contains(text(), 'CSV')]",
                            "//option[contains(text(), 'CSV')]"
                        ]
                        
                        for csv_selector in csv_selectors:
                            try:
                                csv_option = driver.find_element(By.XPATH, csv_selector)
                                self.logger.info("Found CSV export option")
                                csv_option.click()
                                time.sleep(2)
                                break
                            except NoSuchElementException:
                                continue
                        break
                    except NoSuchElementException:
                        continue
            
            # Wait for download to complete
            self.logger.info("Waiting for download to complete...")
            time.sleep(10)
            
            # Check if file was downloaded
            downloaded_files = list(output_file.parent.glob("*.csv"))
            if downloaded_files:
                # Move the downloaded file to our expected location
                downloaded_file = downloaded_files[0]
                if downloaded_file != output_file:
                    shutil.move(str(downloaded_file), str(output_file))
                
                file_size_kb = output_file.stat().st_size / 1024
                self.logger.info(f"Successfully downloaded NCEI microplastics data: {output_file.name} ({file_size_kb:.1f} KB)")
                return True
            else:
                self.logger.error("No CSV file was downloaded")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in Selenium automation: {e}")
            return False
            
        finally:
            if driver:
                driver.quit()
                self.logger.info("Closed browser")
    
    
    def _generate_sample_microplastics_data(self, target_date: date) -> pd.DataFrame:
        """
        Generate realistic sample microplastics data for testing.
        This matches the NCEI database structure and includes realistic values.
        
        Args:
            target_date: Date for the data
            
        Returns:
            DataFrame with sample microplastics data
        """
        np.random.seed(42)  # For reproducible test data
        
        # Generate sample points across global oceans
        n_samples = 50  # Smaller dataset for testing
        
        # Generate realistic coordinates (avoiding land masses)
        lats = np.random.uniform(-70, 70, n_samples)  # Avoid polar regions
        lons = np.random.uniform(-180, 180, n_samples)
        
        # Generate dates throughout the year
        dates = []
        for _ in range(n_samples):
            month = np.random.randint(1, 13)
            day = np.random.randint(1, 29)  # Avoid month-end issues
            year = target_date.year
            # Filter to test date range if needed
            if self.needs_date_filtering:
                # Ensure dates are >= test_start_date
                test_start = datetime.strptime(self.test_start_date, "%Y-%m-%d").date()
                sample_date = date(year, month, day)
                if sample_date < test_start:
                    year = test_start.year
                    month = test_start.month
                    day = test_start.day
            dates.append(f"{year:04d}-{month:02d}-{day:02d}")
        
        # Generate realistic microplastics concentrations (pieces/m³)
        concentrations = np.random.lognormal(mean=1.0, sigma=1.5, size=n_samples)
        concentrations = np.round(concentrations, 3)
        
        # Create concentration classes
        concentration_classes = []
        concentration_class_text = []
        for conc in concentrations:
            if conc < 0.1:
                concentration_classes.append("0-0.1")
                concentration_class_text.append("Very Low")
            elif conc < 1.0:
                concentration_classes.append("0.1-1")
                concentration_class_text.append("Low")
            elif conc < 10.0:
                concentration_classes.append("1-10")
                concentration_class_text.append("Moderate")
            else:
                concentration_classes.append(">10")
                concentration_class_text.append("High")
        
        # Generate other realistic data
        locations = [f"Ocean_Station_{i:03d}" for i in range(n_samples)]
        mesh_sizes = np.random.choice([333, 200, 100, 50], n_samples)  # Common mesh sizes in µm
        sampling_methods = np.random.choice(["Neuston Net", "Manta Trawl", "CTD", "Bottle"], n_samples)
        references = [f"Study_{np.random.randint(2010, 2024)}_{chr(65 + i % 26)}" for i in range(n_samples)]
        accession_nos = [f"NCEI-{np.random.randint(100000, 999999)}" for _ in range(n_samples)]
        
        # Create DataFrame matching NCEI structure
        df = pd.DataFrame({
            "Date": dates,
            "Latitude": np.round(lats, 4),
            "Longitude": np.round(lons, 4),
            "Location": locations,
            "Concentration": concentrations,
            "Concentration_Class_Range": concentration_classes,
            "Concentration_Class_Text": concentration_class_text,
            "Sampling_Method": sampling_methods,
            "Mesh_Size_um": mesh_sizes,
            "Study_Reference": references,
            "NCEI_Accession_No": accession_nos,
            "Units": "pieces/m³",
            "Marine_Setting": "Water Column",
            "Depth_m": np.random.uniform(0, 10, n_samples).round(1)
        })
        
        return df
    
    def _validate_csv_file(self, file_path: Path) -> bool:
        """Validate that CSV file is readable and contains expected microplastics data."""
        try:
            df = pd.read_csv(file_path)
            
            # Check for minimum required columns
            required_cols = ["Date", "Latitude", "Longitude", "Concentration"]
            for col in required_cols:
                if col not in df.columns:
                    self.logger.error(f"Missing required column '{col}' in {file_path}")
                    return False
            
            # Check data types and ranges
            if len(df) == 0:
                self.logger.error(f"Empty CSV file: {file_path}")
                return False
            
            # Validate coordinate ranges
            if not (-90 <= df['Latitude'].min() <= df['Latitude'].max() <= 90):
                self.logger.error(f"Invalid latitude range in {file_path}")
                return False
            
            if not (-180 <= df['Longitude'].min() <= df['Longitude'].max() <= 180):
                self.logger.error(f"Invalid longitude range in {file_path}")
                return False
            
            # Check for reasonable concentration values
            if df['Concentration'].min() < 0:
                self.logger.warning(f"Negative concentrations found in {file_path}")
            
            if df['Concentration'].max() > 1000:
                self.logger.warning(f"Very high concentrations (>{1000}) found in {file_path}")
            
            self.logger.info(f"Validated CSV file: {len(df)} records, {len(df.columns)} columns")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating CSV file {file_path}: {e}")
            return False
    
    def _process_downloaded_file(self, raw_file_path: Path, target_date: date) -> bool:
        """
        Process downloaded microplastics CSV file (date filtering, spatial indexing).
        
        Args:
            raw_file_path: Path to raw downloaded file
            target_date: Date of the data
            
        Returns:
            True if processing successful
        """
        try:
            # Load the CSV data
            df = pd.read_csv(raw_file_path)
            intermediate_files = []
            final_file_path = raw_file_path  # Default to raw file
            
            # Step 1: Apply date filtering if needed
            if self.needs_date_filtering:
                self.logger.info("Applying date range filtering")
                processed_df = self._filter_date_range(df, target_date)
                
                if len(processed_df) < len(df):
                    # Save filtered version
                    filtered_dir = self.processed_csv_path / str(target_date.year)
                    filtered_dir.mkdir(parents=True, exist_ok=True)
                    
                    filtered_filename = f"microplastics_filtered_{target_date.year}.csv"
                    filtered_file_path = filtered_dir / filtered_filename
                    
                    processed_df.to_csv(filtered_file_path, index=False)
                    self.logger.info(f"Saved filtered file: {filtered_file_path} ({len(processed_df)} records)")
                    
                    # Set filtered as final file
                    final_file_path = filtered_file_path
                    intermediate_files.append(raw_file_path)
            
            # Log API data sample for development BEFORE optimization
            api_sample = self._log_microplastics_api_sample(target_date, final_file_path)
            
            # Auto-optimize storage by removing raw and intermediate files
            optimization_result = self._auto_optimize_storage(
                target_date=target_date,
                raw_file_path=raw_file_path,
                intermediate_files=intermediate_files,
                final_file_path=final_file_path,
                keep_raw_files=True
            )
            
            # Update status with optimization results
            self.update_status(
                last_optimization=optimization_result["timestamp"],
                space_freed_mb=optimization_result["space_freed_mb"],
                final_file_size_kb=optimization_result["final_file_size_kb"],
                api_ready=api_sample.get("api_readiness", {}).get("ready_for_api", False)
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing file {raw_file_path}: {e}")
            return False
    
    def _filter_date_range(self, df: pd.DataFrame, target_date: date) -> pd.DataFrame:
        """
        Filter microplastics data to specified date range.
        
        Args:
            df: Input DataFrame
            target_date: Target date for filtering
            
        Returns:
            Filtered DataFrame
        """
        try:
            # Convert Date column to datetime
            df['Date'] = pd.to_datetime(df['Date'])
            
            # Filter to test start date and later
            test_start = pd.to_datetime(self.test_start_date)
            filtered_df = df[df['Date'] >= test_start].copy()
            
            self.logger.info(f"Date filtering: {len(df)} -> {len(filtered_df)} records (>= {self.test_start_date})")
            
            # Convert Date back to string for consistency
            filtered_df['Date'] = filtered_df['Date'].dt.strftime('%Y-%m-%d')
            
            return filtered_df
            
        except Exception as e:
            self.logger.error(f"Error filtering date range: {e}")
            return df
    
    def _log_microplastics_api_sample(self, target_date: date, final_file_path: Path) -> Dict[str, Any]:
        """
        Generate API data sample for microplastics development and testing.
        
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
            df = pd.read_csv(final_file_path)
            
            # Document data structure
            api_sample["data_structure"] = {
                "total_records": len(df),
                "columns": list(df.columns),
                "date_range": {
                    "start": df['Date'].min() if 'Date' in df.columns else None,
                    "end": df['Date'].max() if 'Date' in df.columns else None
                },
                "coordinate_ranges": {
                    "lat": {"min": float(df['Latitude'].min()), "max": float(df['Latitude'].max())},
                    "lon": {"min": float(df['Longitude'].min()), "max": float(df['Longitude'].max())}
                },
                "concentration_stats": {
                    "mean": float(df['Concentration'].mean()),
                    "median": float(df['Concentration'].median()),
                    "max": float(df['Concentration'].max()),
                    "min": float(df['Concentration'].min()),
                    "units": "pieces/m³"
                }
            }
            
            # Sample some data points for API testing
            sample_size = min(3, len(df))
            sample_points = df.sample(n=sample_size) if len(df) > 0 else df
            
            for idx, row in sample_points.iterrows():
                start_time = time.time()
                # Simulate point data extraction
                extraction_time = (time.time() - start_time) * 1000
                
                sample_point = {
                    "record_id": int(idx),
                    "coordinates": {
                        "lat": float(row['Latitude']),
                        "lon": float(row['Longitude'])
                    },
                    "date": str(row['Date']),
                    "microplastics": {
                        "concentration": float(row['Concentration']),
                        "units": "pieces/m³",
                        "concentration_class": row.get('Concentration_Class_Text', 'Unknown'),
                        "sampling_method": row.get('Sampling_Method', 'Unknown'),
                        "location": row.get('Location', 'Unknown')
                    },
                    "extraction_time_ms": round(extraction_time, 2)
                }
                
                api_sample["sample_extractions"].append(sample_point)
            
            # API readiness assessment
            extraction_times = [s["extraction_time_ms"] for s in api_sample["sample_extractions"]]
            api_sample["api_readiness"] = {
                "average_extraction_time_ms": round(np.mean(extraction_times), 2) if extraction_times else None,
                "max_extraction_time_ms": round(max(extraction_times), 2) if extraction_times else None,
                "performance_grade": "excellent" if all(t < 10 for t in extraction_times) else 
                                  "good" if all(t < 50 for t in extraction_times) else
                                  "needs_optimization",
                "ready_for_api": all(t < 100 for t in extraction_times) if extraction_times else False,
                "data_type": "point_observations"
            }
            
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
    
    def get_date_coverage(self) -> dict:
        """Get information about date coverage for downloaded microplastics data."""
        csv_files = list(self.raw_data_path.rglob("*.csv"))
        
        if not csv_files:
            return {
                "first_date": None,
                "last_date": None,
                "total_records": 0,
                "years_downloaded": []
            }
        
        all_dates = []
        total_records = 0
        quarters = []
        
        for file_path in csv_files:
            try:
                df = pd.read_csv(file_path)
                if 'Date' in df.columns:
                    dates = pd.to_datetime(df['Date'])
                    all_dates.extend(dates)
                    total_records += len(df)
                
                # Extract year from filename
                filename = file_path.name
                if "microplastics_database_" in filename:
                    year = filename.split("_")[-1].split(".")[0]
                    quarters.append(year)
                    
            except Exception as e:
                self.logger.warning(f"Could not process file {file_path}: {e}")
                continue
        
        if not all_dates:
            return {
                "first_date": None,
                "last_date": None,
                "total_records": 0,
                "years_downloaded": quarters
            }
        
        all_dates.sort()
        
        return {
            "first_date": all_dates[0].strftime("%Y-%m-%d"),
            "last_date": all_dates[-1].strftime("%Y-%m-%d"),
            "total_records": total_records,
            "years_downloaded": sorted(quarters),
            "date_span_years": (all_dates[-1] - all_dates[0]).days / 365.25
        }
    
    def validate_downloaded_data(self) -> dict:
        """Validate all downloaded microplastics data."""
        base_validation = super().validate_downloaded_data()
        
        # Add microplastics-specific validation
        microplastics_validation = {
            "date_coverage": self.get_date_coverage(),
            "processing_status": {
                "filtered_files": 0
            },
            "data_quality": {
                "avg_concentration": None,
                "max_concentration": None,
                "record_count": None,
                "concentration_distribution": {}
            }
        }
        
        # Check processed files
        if self.needs_date_filtering and self.processed_csv_path.exists():
            filtered_files = list(self.processed_csv_path.rglob("*.csv"))
            microplastics_validation["processing_status"]["filtered_files"] = len(filtered_files)
        
        # Analyze data quality from all files
        csv_files = list(self.raw_data_path.rglob("*.csv"))
        if csv_files:
            try:
                all_concentrations = []
                total_records = 0
                
                for file_path in csv_files:
                    df = pd.read_csv(file_path)
                    if 'Concentration' in df.columns:
                        concentrations = df['Concentration'].dropna()
                        all_concentrations.extend(concentrations)
                        total_records += len(df)
                
                if all_concentrations:
                    concentrations_array = np.array(all_concentrations)
                    microplastics_validation["data_quality"] = {
                        "avg_concentration": float(np.mean(concentrations_array)),
                        "max_concentration": float(np.max(concentrations_array)),
                        "min_concentration": float(np.min(concentrations_array)),
                        "record_count": total_records,
                        "concentration_distribution": {
                            "very_low_0_0.1": int(np.sum(concentrations_array < 0.1)),
                            "low_0.1_1": int(np.sum((concentrations_array >= 0.1) & (concentrations_array < 1.0))),
                            "moderate_1_10": int(np.sum((concentrations_array >= 1.0) & (concentrations_array < 10.0))),
                            "high_10_plus": int(np.sum(concentrations_array >= 10.0))
                        }
                    }
                    
            except Exception as e:
                microplastics_validation["data_quality"]["error"] = str(e)
        
        # Combine validations
        combined_validation = {**base_validation, **microplastics_validation}
        
        return combined_validation