#!/usr/bin/env python3
"""
Extract real ocean data for first 50 reliable coordinates as a test
"""

import xarray as xr
import numpy as np
import pandas as pd
from pathlib import Path
import glob

# Configuration
RAW_DATA_DIR = Path("/media/anecoica/ANECOICA_DEV/pantha-rei-data-viz/ocean-data/raw")
COORDS_FILE = "ocean_coordinates_100_percent_reliable.csv" 
OUTPUT_FILE = "sample_reliable_ocean_data_50_locations.csv"

def extract_data_for_location(location):
    """Extract available data for one location"""
    lat = location['Latitude']
    lon = location['Longitude']
    
    print(f"Processing {location['Location_Name']} ({lat:.1f}, {lon:.1f})")
    
    # Start with metadata
    data = {
        'Location_ID': location['Location_ID'],
        'Location_Name': location['Location_Name'], 
        'Date_Early': location['Date_Early'],
        'Date_Mid': location['Date_Mid'],
        'Date_Late': location['Date_Late'],
        'Latitude': lat,
        'Longitude': lon,
        'Region': location['Region'],
        'Ocean_Basin': location['Ocean_Basin'],
        'Ecosystem_Type': location['Ecosystem_Type'],
        'Climate_Zone': location['Climate_Zone']
    }
    
    # Extract SST data (sample from 2003, 2010, 2025 files)
    try:
        sst_files = list(glob.glob(str(RAW_DATA_DIR / "sst" / "**" / "*.nc"), recursive=True))
        if sst_files:
            # Use different files for different years
            for i, year in enumerate(['2003', '2010', '2025']):
                try:
                    file_idx = (i * len(sst_files) // 3) % len(sst_files)
                    sst_file = sst_files[file_idx]
                    ds = xr.open_dataset(sst_file)
                    
                    # Handle longitude conversion
                    lon_use = lon if lon >= 0 else lon + 360
                    sst_val = ds.sst.isel(time=0).sel(lat=lat, lon=lon_use, method='nearest').values
                    
                    if not np.isnan(sst_val):
                        data[f'SST_{year}_C'] = float(sst_val.item()) 
                    
                    # Sea ice if available
                    if 'ice' in ds.variables:
                        ice_val = ds.ice.isel(time=0).sel(lat=lat, lon=lon_use, method='nearest').values
                        if not np.isnan(ice_val):
                            data[f'Sea_Ice_{year}_percent'] = float(ice_val.item())
                    
                    ds.close()
                except Exception as e:
                    print(f"  SST {year} error: {e}")
                    continue
    except Exception as e:
        print(f"  SST general error: {e}")
    
    # Extract currents data
    try:
        curr_files = list(glob.glob(str(RAW_DATA_DIR / "currents" / "**" / "*.nc"), recursive=True))
        if curr_files:
            curr_file = curr_files[-1]  # Most recent
            ds = xr.open_dataset(curr_file)
            
            u_val = ds.uo.isel(time=0, depth=0).sel(latitude=lat, longitude=lon, method='nearest').values
            v_val = ds.vo.isel(time=0, depth=0).sel(latitude=lat, longitude=lon, method='nearest').values
            
            if not np.isnan(u_val) and not np.isnan(v_val):
                data['Current_U_2025_m_s'] = float(u_val.item())
                data['Current_V_2025_m_s'] = float(v_val.item())
                
                speed = np.sqrt(u_val**2 + v_val**2)
                direction = np.degrees(np.arctan2(v_val, u_val)) % 360
                
                data['Current_Speed_2025_m_s'] = float(speed.item())
                data['Current_Direction_2025_deg'] = float(direction.item())
            
            ds.close()
    except Exception as e:
        print(f"  Currents error: {e}")
    
    # Extract historical biogeochemistry
    try:
        hist_files = list(glob.glob(str(RAW_DATA_DIR / "acidity_historical" / "**" / "*.nc"), recursive=True))
        if hist_files:
            hist_file = hist_files[len(hist_files)//2]  # Middle file
            ds = xr.open_dataset(hist_file)
            
            # Map variables to years
            var_mapping = {
                'chl': ['Chlorophyll_2003_mg_m3', 'Chlorophyll_2010_mg_m3'],
                'no3': ['Nitrate_2003_mmol_m3', 'Nitrate_2010_mmol_m3'], 
                'po4': ['Phosphate_2003_mmol_m3', 'Phosphate_2010_mmol_m3'],
                'si': ['Silicate_2003_mmol_m3', 'Silicate_2010_mmol_m3'],
                'o2': ['Oxygen_2003_mmol_m3', 'Oxygen_2010_mmol_m3'],
                'nppv': ['Marine_Life_Production_2003_mg_m3_day', 'Marine_Life_Production_2010_mg_m3_day']
            }
            
            for var, col_names in var_mapping.items():
                if var in ds.variables:
                    try:
                        val = ds[var].isel(time=0, depth=0).sel(latitude=lat, longitude=lon, method='nearest').values
                        if not np.isnan(val):
                            val_float = float(val.item())
                            for col_name in col_names:
                                data[col_name] = val_float
                    except Exception:
                        continue
            
            ds.close()
    except Exception as e:
        print(f"  Historical biogeochem error: {e}")
    
    # Extract current biogeochemistry  
    try:
        curr_files = list(glob.glob(str(RAW_DATA_DIR / "acidity_current" / "**" / "*.nc"), recursive=True))
        if curr_files:
            curr_file = curr_files[len(curr_files)//2]  # Middle file
            ds = xr.open_dataset(curr_file)
            
            var_mapping = {
                'ph': 'pH_2025',
                'dissic': 'DIC_2025_mmol_m3', 
                'talk': 'Alkalinity_2025_mmol_m3'
            }
            
            for var, col_name in var_mapping.items():
                if var in ds.variables:
                    try:
                        val = ds[var].isel(time=0, depth=0).sel(latitude=lat, longitude=lon, method='nearest').values
                        if not np.isnan(val):
                            data[col_name] = float(val.item())
                    except Exception:
                        continue
            
            ds.close()
    except Exception as e:
        print(f"  Current biogeochem error: {e}")
    
    return data

def main():
    print("🌊 EXTRACTING SAMPLE RELIABLE OCEAN DATA (50 LOCATIONS)")
    print("=" * 55)
    
    # Load coordinates
    coords_df = pd.read_csv(COORDS_FILE)
    sample_coords = coords_df.head(50)  # First 50 locations
    
    print(f"📍 Processing {len(sample_coords)} sample locations")
    
    # Extract data
    results = []
    for i, location in sample_coords.iterrows():
        try:
            location_data = extract_data_for_location(location)
            results.append(location_data)
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue
    
    # Save results
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_FILE, index=False)
    
    print(f"\n✅ Extracted data for {len(results)} locations")
    print(f"📊 Parameters per location: {len(df.columns)}")
    
    # Quality check
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        total_cells = len(df) * len(numeric_cols)
        missing_cells = df[numeric_cols].isnull().sum().sum()
        reliability = (total_cells - missing_cells) / total_cells * 100
        
        print(f"📈 Reliability: {reliability:.1f}%")
        print(f"💾 Saved to: {OUTPUT_FILE}")
    
    # Show sample data
    print(f"\n📋 SAMPLE DATA:")
    key_cols = ['Location_Name', 'SST_2025_C', 'pH_2025', 'Oxygen_2010_mmol_m3', 'Current_Speed_2025_m_s']
    available_cols = [col for col in key_cols if col in df.columns]
    if available_cols:
        print(df[available_cols].head(3).to_string(index=False))

if __name__ == "__main__":
    main()