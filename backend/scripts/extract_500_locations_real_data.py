#!/usr/bin/env python3
"""
Extract real data from NetCDF files for 500 globally distributed ocean locations.
This script creates a comprehensive dataset with all requested parameters using actual NetCDF data.
"""

import xarray as xr
import numpy as np
import pandas as pd
from pathlib import Path
import glob
import warnings
from datetime import datetime
import sys

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Define data directories
OCEAN_DATA_ROOT = Path("/media/anecoica/ANECOICA_DEV/pantha-rei-data-viz/ocean-data")
RAW_DATA_DIR = OCEAN_DATA_ROOT / "raw"
OUTPUT_FILE = "comprehensive_ocean_health_data_500_locations_real_extraction.csv"

def get_ecosystem_type(lat, lon, sst_mean):
    """Classify ecosystem type based on location and SST."""
    if abs(lat) > 66:
        return "Polar_Marine"
    elif abs(lat) > 40:
        if sst_mean < 10:
            return "Subpolar_Marine"
        else:
            return "Temperate_Marine"
    elif abs(lat) > 23.5:
        return "Temperate_Marine"
    elif abs(lat) < 23.5:
        if sst_mean > 25:
            return "Tropical_Marine"
        else:
            return "Subtropical_Marine"
    else:
        return "Temperate_Marine"

def get_climate_zone(lat):
    """Classify climate zone based on latitude."""
    if abs(lat) > 66:
        return "Polar"
    elif abs(lat) > 40:
        return "Temperate"
    elif abs(lat) > 23.5:
        return "Subtropical"
    else:
        return "Tropical"

def get_ocean_basin(lat, lon):
    """Determine ocean basin based on coordinates."""
    # Convert longitude to 0-360 range for easier basin detection
    lon_360 = lon if lon >= 0 else lon + 360
    
    if lat > 65:
        return "Arctic_Ocean"
    elif lat < -60:
        return "Southern_Ocean"
    elif 20 <= lon_360 <= 150 and lat > -35:
        return "Indian_Ocean"
    elif lon_360 > 150 or lon_360 < 20:
        return "Pacific_Ocean"
    else:
        return "Atlantic_Ocean"

def generate_500_locations():
    """Generate 500 globally distributed ocean locations."""
    locations = []
    location_id = 1
    
    # Arctic Ocean (50 locations)
    for i in range(50):
        lat = np.random.uniform(65, 85)
        lon = np.random.uniform(-180, 180)
        locations.append({
            'id': location_id,
            'name': f'ARC_{location_id:03d}',
            'lat': lat,
            'lon': lon,
            'region': 'Arctic',
            'ocean_basin': get_ocean_basin(lat, lon)
        })
        location_id += 1
    
    # North Pacific (100 locations)
    for i in range(100):
        lat = np.random.uniform(0, 65)
        lon = np.random.uniform(130, 240)  # 130E to 120W
        if lon > 180:
            lon -= 360
        locations.append({
            'id': location_id,
            'name': f'NPac_{location_id:03d}',
            'lat': lat,
            'lon': lon,
            'region': 'North_Pacific',
            'ocean_basin': get_ocean_basin(lat, lon)
        })
        location_id += 1
    
    # South Pacific (75 locations)
    for i in range(75):
        lat = np.random.uniform(-65, 0)
        lon = np.random.uniform(130, 240)
        if lon > 180:
            lon -= 360
        locations.append({
            'id': location_id,
            'name': f'SPac_{location_id:03d}',
            'lat': lat,
            'lon': lon,
            'region': 'South_Pacific',
            'ocean_basin': get_ocean_basin(lat, lon)
        })
        location_id += 1
    
    # North Atlantic (75 locations)
    for i in range(75):
        lat = np.random.uniform(0, 65)
        lon = np.random.uniform(-80, 20)
        locations.append({
            'id': location_id,
            'name': f'NAtl_{location_id:03d}',
            'lat': lat,
            'lon': lon,
            'region': 'North_Atlantic',
            'ocean_basin': get_ocean_basin(lat, lon)
        })
        location_id += 1
    
    # South Atlantic (75 locations)
    for i in range(75):
        lat = np.random.uniform(-65, 0)
        lon = np.random.uniform(-70, 20)
        locations.append({
            'id': location_id,
            'name': f'SAtl_{location_id:03d}',
            'lat': lat,
            'lon': lon,
            'region': 'South_Atlantic',
            'ocean_basin': get_ocean_basin(lat, lon)
        })
        location_id += 1
    
    # Indian Ocean (75 locations)
    for i in range(75):
        lat = np.random.uniform(-65, 30)
        lon = np.random.uniform(20, 120)
        locations.append({
            'id': location_id,
            'name': f'Ind_{location_id:03d}',
            'lat': lat,
            'lon': lon,
            'region': 'Indian_Ocean',
            'ocean_basin': get_ocean_basin(lat, lon)
        })
        location_id += 1
    
    # Equatorial belt (50 locations)
    for i in range(50):
        lat = np.random.uniform(-15, 15)
        lon = np.random.uniform(-180, 180)
        locations.append({
            'id': location_id,
            'name': f'Eq_{location_id:03d}',
            'lat': lat,
            'lon': lon,
            'region': 'Equatorial',
            'ocean_basin': get_ocean_basin(lat, lon)
        })
        location_id += 1
    
    # Southern Ocean (75 locations)
    for i in range(75):
        lat = np.random.uniform(-70, -45)
        lon = np.random.uniform(-180, 180)
        locations.append({
            'id': location_id,
            'name': f'SO_{location_id:03d}',
            'lat': lat,
            'lon': lon,
            'region': 'Southern_Ocean',
            'ocean_basin': get_ocean_basin(lat, lon)
        })
        location_id += 1
    
    return locations

def get_netcdf_files():
    """Get available NetCDF files for each dataset type."""
    files = {
        'sst': [],
        'currents': [],
        'acidity_historical': [],
        'acidity_current': []
    }
    
    # SST files - recursive search
    sst_pattern = str(RAW_DATA_DIR / "sst" / "**" / "*.nc")
    files['sst'] = sorted(glob.glob(sst_pattern, recursive=True))
    print(f"Found {len(files['sst'])} SST files")
    
    # Currents files - recursive search
    currents_pattern = str(RAW_DATA_DIR / "currents" / "**" / "*.nc")
    files['currents'] = sorted(glob.glob(currents_pattern, recursive=True))
    print(f"Found {len(files['currents'])} currents files")
    
    # Historical acidity files - recursive search
    acidity_hist_pattern = str(RAW_DATA_DIR / "acidity_historical" / "**" / "*.nc")
    files['acidity_historical'] = sorted(glob.glob(acidity_hist_pattern, recursive=True))
    print(f"Found {len(files['acidity_historical'])} historical acidity files")
    
    # Current acidity files - recursive search
    acidity_curr_pattern = str(RAW_DATA_DIR / "acidity_current" / "**" / "*.nc")
    files['acidity_current'] = sorted(glob.glob(acidity_curr_pattern, recursive=True))
    print(f"Found {len(files['acidity_current'])} current acidity files")
    
    return files

def extract_sst_data(location, files, target_years=[2003, 2010, 2025]):
    """Extract SST data for target years."""
    sst_data = {}
    
    for year in target_years:
        # Find files from the target year with more flexible matching
        year_files = [f for f in files if f"/{year}/" in f or f"sst_{year}" in f or f"{year}01" in f]
        
        if not year_files:
            # Find closest available year
            available_years = []
            for f in files:
                try:
                    # Extract year from path or filename
                    if f"/{year}/" in f:
                        file_year = year
                    else:
                        # Try various patterns to extract year
                        parts = f.replace('/', '_').split('_')
                        for part in parts:
                            if part.isdigit() and len(part) == 4 and 1990 <= int(part) <= 2030:
                                file_year = int(part)
                                available_years.append(file_year)
                                break
                except:
                    continue
            
            if available_years:
                closest_year = min(set(available_years), key=lambda x: abs(x - year))
                year_files = [f for f in files if f"/{closest_year}/" in f or f"sst_{closest_year}" in f]
        
        if year_files:
            try:
                # Use first available file for the year
                ds = xr.open_dataset(year_files[0])
                
                # Convert longitude for SST (SST uses 0-360, need to match location)
                target_lon = location['lon'] if location['lon'] >= 0 else location['lon'] + 360
                
                # Extract data at location
                sst_val = ds.sst.sel(lat=location['lat'], lon=target_lon, method='nearest')
                anom_val = ds.anom.sel(lat=location['lat'], lon=target_lon, method='nearest') if 'anom' in ds else np.nan
                ice_val = ds.ice.sel(lat=location['lat'], lon=target_lon, method='nearest') if 'ice' in ds else 0
                
                sst_data[f'SST_{year}_C'] = float(sst_val.values) if not np.isnan(sst_val.values) else np.nan
                sst_data[f'SST_Anomaly_{year}_C'] = float(anom_val.values) if not np.isnan(anom_val.values) else np.nan
                sst_data[f'Sea_Ice_{year}_percent'] = float(ice_val.values) if not np.isnan(ice_val.values) else 0
                
                ds.close()
            except Exception as e:
                print(f"Error extracting SST for {year}: {e}")
                sst_data[f'SST_{year}_C'] = np.nan
                sst_data[f'SST_Anomaly_{year}_C'] = np.nan
                sst_data[f'Sea_Ice_{year}_percent'] = 0
        else:
            sst_data[f'SST_{year}_C'] = np.nan
            sst_data[f'SST_Anomaly_{year}_C'] = np.nan
            sst_data[f'Sea_Ice_{year}_percent'] = 0
    
    return sst_data

def extract_biochem_data(location, files, target_years, dataset_type):
    """Extract biochemistry data."""
    biochem_data = {}
    
    for year in target_years:
        # Find files from the target year
        year_files = [f for f in files if f"/{year}/" in f or f"_{year}" in f]
        if not year_files:
            continue
            
        try:
            ds = xr.open_dataset(year_files[0])
            
            # Biochemistry uses -180 to 180 longitude
            target_lon = location['lon']
            
            if dataset_type == 'historical':
                variables = ['chl', 'no3', 'po4', 'si', 'o2', 'nppv']
                var_names = ['Chlorophyll', 'Nitrate', 'Phosphate', 'Silicate', 'Oxygen', 'Primary_Production']
                units = ['mg_m3', 'mmol_m3', 'mmol_m3', 'mmol_m3', 'mmol_m3', 'mg_m3_day']
            else:  # current
                variables = ['ph', 'dissic', 'talk']
                var_names = ['pH', 'DIC', 'Alkalinity']
                units = ['', 'mol_m3', 'mol_m3']
            
            for var, name, unit in zip(variables, var_names, units):
                if var in ds:
                    val = ds[var].sel(latitude=location['lat'], longitude=target_lon, method='nearest')
                    # Use surface data (first depth level)
                    if 'depth' in val.dims:
                        val = val.isel(depth=0)
                    
                    key = f'{name}_{year}' if not unit else f'{name}_{year}_{unit}'
                    biochem_data[key] = float(val.values) if not np.isnan(val.values) else np.nan
            
            ds.close()
        except Exception as e:
            print(f"Error extracting biochemistry for {year}: {e}")
    
    return biochem_data

def extract_currents_data(location, files):
    """Extract ocean currents data for 2025."""
    currents_data = {}
    
    # Look for 2025 files first, then fall back to most recent
    recent_files = [f for f in files if "/2025/" in f]
    if not recent_files:
        recent_files = files[-10:] if files else []  # Use last 10 files if available
    
    if recent_files:
        try:
            ds = xr.open_dataset(recent_files[0])
            
            # Currents use latitude/longitude
            u_val = ds.uo.sel(latitude=location['lat'], longitude=location['lon'], method='nearest')
            v_val = ds.vo.sel(latitude=location['lat'], longitude=location['lon'], method='nearest')
            
            # Use surface data (first depth level)
            if 'depth' in u_val.dims:
                u_val = u_val.isel(depth=0)
                v_val = v_val.isel(depth=0)
            
            u = float(u_val.values) if not np.isnan(u_val.values) else 0
            v = float(v_val.values) if not np.isnan(v_val.values) else 0
            
            # Calculate speed and direction
            speed = np.sqrt(u**2 + v**2)
            direction = np.degrees(np.arctan2(v, u)) % 360
            
            currents_data['Current_U_2025_m_s'] = u
            currents_data['Current_V_2025_m_s'] = v
            currents_data['Current_Speed_2025_m_s'] = speed
            currents_data['Current_Direction_2025_deg'] = direction
            
            ds.close()
        except Exception as e:
            print(f"Error extracting currents: {e}")
            currents_data['Current_U_2025_m_s'] = 0
            currents_data['Current_V_2025_m_s'] = 0
            currents_data['Current_Speed_2025_m_s'] = 0
            currents_data['Current_Direction_2025_deg'] = 0
    else:
        currents_data['Current_U_2025_m_s'] = 0
        currents_data['Current_V_2025_m_s'] = 0
        currents_data['Current_Speed_2025_m_s'] = 0
        currents_data['Current_Direction_2025_deg'] = 0
    
    return currents_data

def main():
    print("Starting extraction of 500 locations with real NetCDF data...")
    
    # Generate locations
    locations = generate_500_locations()
    print(f"Generated {len(locations)} locations")
    
    # Get NetCDF files
    files = get_netcdf_files()
    
    # Initialize results
    results = []
    
    print("Extracting data for each location...")
    for i, location in enumerate(locations):
        if i % 50 == 0:
            print(f"Processing location {i+1}/{len(locations)}")
        
        # Initialize location data
        location_data = {
            'Location_ID': location['id'],
            'Location_Name': location['name'],
            'Date_Early': '2003-01-15',
            'Date_Mid': '2010-01-15',
            'Date_Late': '2025-01-15',
            'Latitude': round(location['lat'], 2),
            'Longitude': round(location['lon'], 2),
            'Region': location['region'],
            'Ocean_Basin': location['ocean_basin']
        }
        
        # Extract SST data
        sst_data = extract_sst_data(location, files['sst'])
        location_data.update(sst_data)
        
        # Calculate mean SST for ecosystem classification
        sst_values = [v for k, v in sst_data.items() if 'SST_' in k and '_C' in k and not np.isnan(v)]
        sst_mean = np.mean(sst_values) if sst_values else 15.0
        
        # Add ecosystem and climate classifications
        location_data['Ecosystem_Type'] = get_ecosystem_type(location['lat'], location['lon'], sst_mean)
        location_data['Climate_Zone'] = get_climate_zone(location['lat'])
        
        # Extract historical biochemistry (2003, 2010)
        if files['acidity_historical']:
            biochem_hist = extract_biochem_data(location, files['acidity_historical'], [2003, 2010], 'historical')
            location_data.update(biochem_hist)
        
        # Extract current biochemistry (2025)
        if files['acidity_current']:
            biochem_curr = extract_biochem_data(location, files['acidity_current'], [2025], 'current')
            location_data.update(biochem_curr)
        
        # Extract currents data
        if files['currents']:
            currents_data = extract_currents_data(location, files['currents'])
            location_data.update(currents_data)
        
        results.append(location_data)
    
    # Create DataFrame and save
    df = pd.DataFrame(results)
    
    # Ensure all expected columns exist
    expected_columns = [
        'Location_ID', 'Location_Name', 'Date_Early', 'Date_Mid', 'Date_Late',
        'Latitude', 'Longitude', 'Region', 'Ocean_Basin', 'Ecosystem_Type', 'Climate_Zone',
        'SST_2003_C', 'SST_2010_C', 'SST_2025_C',
        'SST_Anomaly_2003_C', 'SST_Anomaly_2010_C', 'SST_Anomaly_2025_C',
        'Sea_Ice_2003_percent', 'Sea_Ice_2010_percent', 'Sea_Ice_2025_percent',
        'Chlorophyll_2003_mg_m3', 'Chlorophyll_2010_mg_m3',
        'Nitrate_2003_mmol_m3', 'Nitrate_2010_mmol_m3',
        'Phosphate_2003_mmol_m3', 'Phosphate_2010_mmol_m3',
        'Silicate_2003_mmol_m3', 'Silicate_2010_mmol_m3',
        'Oxygen_2003_mmol_m3', 'Oxygen_2010_mmol_m3',
        'Primary_Production_2003_mg_m3_day', 'Primary_Production_2010_mg_m3_day',
        'pH_2025', 'DIC_2025_mol_m3', 'Alkalinity_2025_mol_m3',
        'Current_U_2025_m_s', 'Current_V_2025_m_s', 'Current_Speed_2025_m_s', 'Current_Direction_2025_deg'
    ]
    
    # Add missing columns with NaN
    for col in expected_columns:
        if col not in df.columns:
            df[col] = np.nan
    
    # Reorder columns
    df = df[expected_columns]
    
    # Save to CSV
    output_path = Path(OUTPUT_FILE)
    df.to_csv(output_path, index=False)
    print(f"\nSaved comprehensive dataset to: {output_path}")
    print(f"Dataset contains {len(df)} locations with {len(df.columns)} parameters")
    
    # Print summary statistics
    print("\nSummary Statistics:")
    print(f"- Locations by region:")
    print(df['Region'].value_counts())
    print(f"\n- Locations by ocean basin:")
    print(df['Ocean_Basin'].value_counts())
    print(f"\n- Locations by ecosystem type:")
    print(df['Ecosystem_Type'].value_counts())

if __name__ == "__main__":
    main()