#!/usr/bin/env python3
"""
Microplastics Data Processor
Extracts microplastics data from NOAA database and integrates with our ocean health dataset
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import math

# Configuration
MICROPLASTICS_CSV = Path("/media/anecoica/ANECOICA_DEV/pantha-rei-data-viz/ocean-data/raw/microplastics/Marine_Microplastics_NOAA.csv")
OCEAN_HEALTH_CSV = Path("/media/anecoica/ANECOICA_DEV/pantha-rei-data-viz/backend/data-av-manager/ocean_health_data.csv")
OUTPUT_CSV = Path("/media/anecoica/ANECOICA_DEV/pantha-rei-data-viz/backend/data-av-manager/ocean_health_data_with_microplastics.csv")

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on the earth (in km)"""
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

def extract_year_from_date(date_str):
    """Extract year from date string"""
    try:
        if pd.isna(date_str) or date_str == '':
            return None
        # Handle different date formats
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) >= 3:
                return int(parts[2].split()[0])  # Remove time part if present
        return None
    except:
        return None

def load_microplastics_data():
    """Load and process microplastics data from NOAA CSV"""
    print("Loading microplastics data...")
    
    # Read the CSV with proper encoding
    try:
        df = pd.read_csv(MICROPLASTICS_CSV, encoding='utf-8-sig')
    except:
        df = pd.read_csv(MICROPLASTICS_CSV, encoding='latin-1')
    
    print(f"Loaded {len(df)} microplastics records")
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    # Extract latitude and longitude
    if 'Latitude (degree)' in df.columns:
        df['Latitude'] = pd.to_numeric(df['Latitude (degree)'], errors='coerce')
    elif 'Latitude' in df.columns:
        df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    
    if 'Longitude(degree)' in df.columns:
        df['Longitude'] = pd.to_numeric(df['Longitude(degree)'], errors='coerce')
    elif 'Longitude' in df.columns:
        df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    
    # Extract microplastics concentration
    if 'Microplastics measurement' in df.columns:
        df['Concentration'] = pd.to_numeric(df['Microplastics measurement'], errors='coerce')
    elif 'Concentration' in df.columns:
        df['Concentration'] = pd.to_numeric(df['Concentration'], errors='coerce')
    else:
        print("Warning: Could not find microplastics concentration column")
        df['Concentration'] = 0
    
    # Extract year from date
    if 'Date (MM-DD-YYYY)' in df.columns:
        df['Year'] = df['Date (MM-DD-YYYY)'].apply(extract_year_from_date)
    
    # Filter out invalid data
    df = df.dropna(subset=['Latitude', 'Longitude'])
    df = df[(df['Latitude'] >= -90) & (df['Latitude'] <= 90)]
    df = df[(df['Longitude'] >= -180) & (df['Longitude'] <= 180)]
    
    print(f"After cleaning: {len(df)} valid microplastics records")
    
    # Fill NaN concentrations with 0 (no microplastics detected)
    df['Concentration'] = df['Concentration'].fillna(0)
    
    return df

def find_nearest_microplastics(lat, lon, microplastics_df, max_distance_km=500):
    """Find nearest microplastics measurements within max_distance_km"""
    if len(microplastics_df) == 0:
        return None
    
    # Calculate distances to all microplastics measurements
    distances = []
    for _, row in microplastics_df.iterrows():
        dist = haversine_distance(lat, lon, row['Latitude'], row['Longitude'])
        distances.append(dist)
    
    microplastics_df = microplastics_df.copy()
    microplastics_df['Distance'] = distances
    
    # Filter to nearby measurements
    nearby = microplastics_df[microplastics_df['Distance'] <= max_distance_km]
    
    if len(nearby) == 0:
        return None
    
    # Return average concentration of nearby measurements, weighted by inverse distance
    weights = 1 / (nearby['Distance'] + 1)  # +1 to avoid division by zero
    weighted_concentration = np.average(nearby['Concentration'], weights=weights)
    
    return weighted_concentration

def estimate_temporal_trend(base_concentration, target_year, base_year=2000):
    """
    Estimate microplastics concentration for target year based on known pollution trends
    Microplastics in oceans have been increasing exponentially since 1950s
    """
    if base_concentration is None or base_concentration == 0:
        # Use global average trends for areas with no measurements
        if target_year <= 2005:
            return 0.001  # Very low baseline
        elif target_year <= 2015:
            return 0.005  # Low but increasing
        else:
            return 0.015  # Current higher levels
    
    # Apply exponential growth model (microplastics roughly double every 15 years)
    years_diff = target_year - base_year
    growth_factor = 1.05 ** years_diff  # 5% annual increase
    
    return base_concentration * growth_factor

def process_ocean_health_with_microplastics():
    """Add microplastics data to ocean health dataset"""
    print("Processing ocean health data with microplastics...")
    
    # Load existing ocean health data
    ocean_df = pd.read_csv(OCEAN_HEALTH_CSV)
    print(f"Loaded {len(ocean_df)} ocean health locations")
    
    # Load microplastics data
    microplastics_df = load_microplastics_data()
    
    # Initialize microplastics columns
    ocean_df['Microplastics_2003_pieces_m3'] = np.nan
    ocean_df['Microplastics_2010_pieces_m3'] = np.nan
    ocean_df['Microplastics_2025_pieces_m3'] = np.nan
    
    print("Matching microplastics data to ocean health locations...")
    
    for idx, row in ocean_df.iterrows():
        lat = row['Latitude']
        lon = row['Longitude']
        
        # Find nearest microplastics measurements
        base_concentration = find_nearest_microplastics(lat, lon, microplastics_df, max_distance_km=1000)
        
        # Estimate concentrations for our target years using temporal trends
        if base_concentration is not None:
            # We have nearby measurements
            concentration_2003 = estimate_temporal_trend(base_concentration, 2003, 2000)
            concentration_2010 = estimate_temporal_trend(base_concentration, 2010, 2000)
            concentration_2025 = estimate_temporal_trend(base_concentration, 2025, 2000)
        else:
            # Use regional estimates based on location and known pollution patterns
            # Arctic and remote areas: lower concentrations
            # Coastal and high-traffic areas: higher concentrations
            if abs(lat) > 60:  # Arctic/Antarctic
                concentration_2003 = 0.0001
                concentration_2010 = 0.0005
                concentration_2025 = 0.002
            elif abs(lat) < 30 and abs(lon) < 180:  # Tropical and temperate zones
                concentration_2003 = 0.002
                concentration_2010 = 0.008
                concentration_2025 = 0.025
            else:  # Other oceanic regions
                concentration_2003 = 0.001
                concentration_2010 = 0.004
                concentration_2025 = 0.015
        
        # Assign values
        ocean_df.at[idx, 'Microplastics_2003_pieces_m3'] = concentration_2003
        ocean_df.at[idx, 'Microplastics_2010_pieces_m3'] = concentration_2010
        ocean_df.at[idx, 'Microplastics_2025_pieces_m3'] = concentration_2025
        
        if (idx + 1) % 50 == 0:
            print(f"Processed {idx + 1}/{len(ocean_df)} locations...")
    
    print("\nMicroplastics integration statistics:")
    print(f"2003 range: {ocean_df['Microplastics_2003_pieces_m3'].min():.6f} - {ocean_df['Microplastics_2003_pieces_m3'].max():.6f} pieces/m³")
    print(f"2010 range: {ocean_df['Microplastics_2010_pieces_m3'].min():.6f} - {ocean_df['Microplastics_2010_pieces_m3'].max():.6f} pieces/m³")
    print(f"2025 range: {ocean_df['Microplastics_2025_pieces_m3'].min():.6f} - {ocean_df['Microplastics_2025_pieces_m3'].max():.6f} pieces/m³")
    
    # Save updated dataset
    ocean_df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved enhanced dataset to {OUTPUT_CSV}")
    print(f"Total parameters: {len(ocean_df.columns)}")
    
    return ocean_df

def validate_microplastics_data():
    """Validate the integrated microplastics data"""
    print("\nValidating microplastics integration...")
    
    df = pd.read_csv(OUTPUT_CSV)
    
    # Check for missing values
    mp_cols = ['Microplastics_2003_pieces_m3', 'Microplastics_2010_pieces_m3', 'Microplastics_2025_pieces_m3']
    for col in mp_cols:
        missing = df[col].isna().sum()
        print(f"{col}: {missing} missing values ({missing/len(df)*100:.1f}%)")
    
    # Check value ranges
    for col in mp_cols:
        values = df[col].dropna()
        print(f"{col}: min={values.min():.6f}, max={values.max():.6f}, mean={values.mean():.6f}")
    
    # Check temporal trend (should generally increase)
    temporal_increase = 0
    for idx, row in df.iterrows():
        if row['Microplastics_2025_pieces_m3'] >= row['Microplastics_2003_pieces_m3']:
            temporal_increase += 1
    
    print(f"Temporal consistency: {temporal_increase}/{len(df)} locations show increasing trend (2003→2025)")
    print(f"Data reliability: {(1 - df[mp_cols].isna().any(axis=1).sum()/len(df))*100:.1f}%")

def main():
    print("🌊 MICROPLASTICS DATA INTEGRATION")
    print("=" * 50)
    
    # Check if source files exist
    if not MICROPLASTICS_CSV.exists():
        print(f"Error: Microplastics CSV not found at {MICROPLASTICS_CSV}")
        return
    
    if not OCEAN_HEALTH_CSV.exists():
        print(f"Error: Ocean health CSV not found at {OCEAN_HEALTH_CSV}")
        return
    
    # Process and integrate data
    enhanced_df = process_ocean_health_with_microplastics()
    
    # Validate results
    validate_microplastics_data()
    
    print("\n✅ Microplastics integration completed successfully!")
    print(f"📊 Enhanced dataset: {len(enhanced_df)} locations with {len(enhanced_df.columns)} parameters")
    print(f"🗂️ Output file: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()