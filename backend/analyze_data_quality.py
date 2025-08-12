#!/usr/bin/env python3
"""Analyze data quality issues in the ocean health CSV"""

import pandas as pd
import numpy as np

# Load the CSV and analyze data quality
df = pd.read_csv('data-av-manager/ocean_health_data.csv')

print('=== CSV DATA QUALITY ANALYSIS ===')
print(f'Total locations: {len(df)}')
print()

# Check for missing values and zeros across key parameters
key_params = [
    'SST_2003_C', 'SST_2010_C', 'SST_2025_C',
    'Chlorophyll_2003_mg_m3', 'Chlorophyll_2010_mg_m3', 
    'Nitrate_2003_mmol_m3', 'Nitrate_2010_mmol_m3',
    'Oxygen_2003_mmol_m3', 'Oxygen_2010_mmol_m3',
    'Marine_Life_Production_2003_mg_m3_day', 'Marine_Life_Production_2010_mg_m3_day',
    'pH_2025', 'Current_Speed_2025_m_s'
]

print('DATA COMPLETENESS BY PARAMETER:')
for param in key_params:
    if param in df.columns:
        total_count = len(df)
        null_count = df[param].isnull().sum()
        zero_count = (df[param] == 0).sum()
        valid_count = ((df[param].notna()) & (df[param] != 0)).sum()
        
        print(f'{param:35s}: {valid_count:3d}/{total_count} valid ({valid_count/total_count*100:5.1f}%), {null_count:3d} missing, {zero_count:3d} zeros')

print()
print('=== LOCATIONS WITH MOST MISSING DATA ===')
# Count missing values per location
missing_counts = df.isnull().sum(axis=1)
worst_locations = df.loc[missing_counts.nlargest(10).index, ['Location_Name', 'Region', 'Latitude', 'Longitude']]
for idx, row in worst_locations.iterrows():
    missing = missing_counts[idx]
    print(f'{row.Location_Name:10s} ({row.Region:15s}): {missing:2d}/39 missing ({missing/39*100:4.1f}%)')

print()
print('=== ZERO VALUES ANALYSIS ===')
# Check why we have zeros - are they valid measurements or missing data?
for param in ['SST_2003_C', 'Oxygen_2003_mmol_m3', 'Current_Speed_2025_m_s', 'Marine_Life_Production_2003_mg_m3_day']:
    if param in df.columns:
        zero_locations = df[df[param] == 0]
        if len(zero_locations) > 0:
            print(f'{param}:')
            print(f'  {len(zero_locations)} locations with zero values')
            if len(zero_locations) > 0:
                print(f'  Sample locations: {list(zero_locations["Location_Name"].head(3))}')
                print(f'  Regions: {list(zero_locations["Region"].value_counts().head(3).index)}')
            print()

print()
print('=== POTENTIAL CAUSES OF DATA ISSUES ===')
print('1. NetCDF coordinate mismatch - some locations may be over land')
print('2. Arctic data gaps - limited coverage in polar regions')  
print('3. Different dataset temporal coverage - not all variables available for all years')
print('4. Data extraction coordinate system conflicts (0-360° vs -180-180°)')
print('5. Missing data in source NetCDF files themselves')

print()
print('=== RELIABILITY ASSESSMENT ===')
# Calculate overall data reliability
total_cells = len(df) * len(key_params)
missing_cells = sum([df[param].isnull().sum() for param in key_params if param in df.columns])
zero_cells = sum([(df[param] == 0).sum() for param in key_params if param in df.columns])
reliable_cells = total_cells - missing_cells - zero_cells

print(f'Total data cells: {total_cells}')
print(f'Missing data: {missing_cells} ({missing_cells/total_cells*100:.1f}%)')
print(f'Zero values: {zero_cells} ({zero_cells/total_cells*100:.1f}%)')
print(f'Reliable data: {reliable_cells} ({reliable_cells/total_cells*100:.1f}%)')

# Check if this is related to the original NetCDF extraction process
print()
print('=== NEED TO INVESTIGATE ===')
print('This data reliability issue suggests problems in the NetCDF extraction process.')
print('We should verify:')
print('- Coordinate system matching between datasets')
print('- Whether locations are actually over ocean vs land')
print('- Temporal availability of each dataset type')
print('- Original NetCDF data completeness')