#!/usr/bin/env python3
"""
Demonstrate Temporal Logic
Shows exactly how 3 time points become 1 sonification value
"""

import pandas as pd
import numpy as np
from pathlib import Path

def demonstrate_temporal_logic():
    """Show temporal aggregation for sample locations"""
    print("🕐 TEMPORAL LOGIC DEMONSTRATION")
    print("=" * 50)
    
    # Load the dataset
    csv_file = Path("/media/anecoica/ANECOICA_DEV/pantha-rei-data-viz/backend/data-av-manager/ocean_health_data.csv")
    df = pd.read_csv(csv_file)
    
    # Select 3 representative locations
    sample_locations = df.iloc[[0, 100, 250]]  # Equatorial, mid-dataset, Arctic-ish
    
    print("📊 SAMPLE LOCATIONS WITH TEMPORAL DATA:")
    print("-" * 50)
    
    for idx, location in sample_locations.iterrows():
        print(f"\n🌍 LOCATION: {location['Location_Name']} ({location['Region']})")
        print(f"   Coordinates: {location['Latitude']:.1f}°, {location['Longitude']:.1f}°")
        print()
        
        # Temperature example
        print("🌡️ TEMPERATURE STRATEGY:")
        temp_2003 = location.get('SST_2003_C', 'N/A')
        temp_2010 = location.get('SST_2010_C', 'N/A')
        temp_2025 = location.get('SST_2025_C', 'N/A')
        
        print(f"   2003: {temp_2003:.2f}°C" if pd.notna(temp_2003) else "   2003: Missing")
        print(f"   2010: {temp_2010:.2f}°C" if pd.notna(temp_2010) else "   2010: Missing")
        print(f"   2025: {temp_2025:.2f}°C" if pd.notna(temp_2025) else "   2025: Missing")
        
        # Show JavaScript logic
        js_temp = temp_2025 if pd.notna(temp_2025) else 15.0
        print(f"   → JS OUTPUT: {js_temp:.2f}°C (uses 2025 value)")
        
        # Show trend calculation
        if pd.notna(temp_2003) and pd.notna(temp_2025):
            warming_trend = temp_2025 - temp_2003
            print(f"   → TREND: {warming_trend:+.2f}°C over 22 years (used in threat score)")
        print()
        
        # Microplastics example
        print("🗑️ MICROPLASTICS STRATEGY:")
        mp_2003 = location.get('Microplastics_2003_pieces_m3', 'N/A')
        mp_2010 = location.get('Microplastics_2010_pieces_m3', 'N/A')
        mp_2025 = location.get('Microplastics_2025_pieces_m3', 'N/A')
        
        print(f"   2003: {mp_2003:.6f} pieces/m³" if pd.notna(mp_2003) else "   2003: Missing")
        print(f"   2010: {mp_2010:.6f} pieces/m³" if pd.notna(mp_2010) else "   2010: Missing")
        print(f"   2025: {mp_2025:.6f} pieces/m³" if pd.notna(mp_2025) else "   2025: Missing")
        
        # Show JavaScript logic
        js_mp = mp_2025 if pd.notna(mp_2025) else 0.005
        print(f"   → JS OUTPUT: {js_mp:.6f} pieces/m³ (uses 2025 value)")
        
        # Show acceleration calculation
        if pd.notna(mp_2003) and pd.notna(mp_2025) and mp_2003 > 0:
            acceleration = mp_2025 / mp_2003
            print(f"   → ACCELERATION: {acceleration:.1f}x increase (used in threat score)")
        print()
        
        # Sea ice example (when available)
        if pd.notna(location.get('Sea_Ice_2025_percent')):
            print("🧊 SEA ICE STRATEGY:")
            ice_2003 = location.get('Sea_Ice_2003_percent', 'N/A')
            ice_2010 = location.get('Sea_Ice_2010_percent', 'N/A') 
            ice_2025 = location.get('Sea_Ice_2025_percent', 'N/A')
            
            print(f"   2003: {ice_2003:.1f}%" if pd.notna(ice_2003) else "   2003: Missing")
            print(f"   2010: {ice_2010:.1f}%" if pd.notna(ice_2010) else "   2010: Missing")
            print(f"   2025: {ice_2025:.1f}%" if pd.notna(ice_2025) else "   2025: Missing")
            
            js_ice = ice_2025 if pd.notna(ice_2025) else 0.0
            print(f"   → JS OUTPUT: {js_ice:.1f}% (uses 2025 value)")
        
        print("─" * 40)

def show_health_score_temporal_logic():
    """Demonstrate health score temporal aggregation"""
    print("\n🏥 HEALTH SCORE TEMPORAL LOGIC")
    print("=" * 35)
    print()
    
    print("Health Score = Weighted Composite Using:")
    print("  📊 30% - Temperature Health (2025 SST)")
    print("  🧪 25% - pH Health (2025 pH)")  
    print("  💨 25% - Oxygen Health (2010 O2 - best data)")
    print("  🌱 10% - Productivity Health (2010 Chlorophyll)")
    print("  🌊 10% - Current Health (2025 current speed)")
    print("  🗑️ 10% - Pollution Health (2025 microplastics)")
    print()
    print("🔄 WHY MIXED TIME PERIODS:")
    print("  • 2025 data: Current crisis state")
    print("  • 2010 data: Best historical coverage for O2/Chlorophyll")
    print("  • Result: Most scientifically accurate composite")

def show_threat_level_temporal_logic():
    """Demonstrate threat level temporal aggregation"""
    print("\n⚠️ THREAT LEVEL TEMPORAL LOGIC")
    print("=" * 32)
    print()
    
    print("Threat Level = Weighted Composite Using:")
    print("  🔥 35% - Warming Trend (2025 SST - 2003 SST)")
    print("  🧪 25% - Current Acidification (2025 pH)")
    print("  💨 25% - Current Oxygen Depletion (2010 O2)")
    print("  🌡️ 10% - Extreme Temperature (2025 SST vs 20°C)")
    print("  🗑️  5% - Pollution Level (2025 microplastics)")
    print()
    print("🎯 WHY TRENDS MATTER:")
    print("  • Static values: Show current state")
    print("  • Temporal trends: Show rate of change")
    print("  • Threat = Current danger + Change velocity")

def main():
    demonstrate_temporal_logic()
    show_health_score_temporal_logic()
    show_threat_level_temporal_logic()
    
    print("\n" + "=" * 60)
    print("🎵 SUMMARY: TEMPORAL AGGREGATION STRATEGY")
    print("=" * 60)
    print()
    print("1️⃣ PRIMARY OUTLETS: Use 2025 (current state)")
    print("   temperature_raw, microplastics_raw, ph_raw, etc.")
    print()
    print("2️⃣ COMPOSITE SCORES: Mix optimal time periods")
    print("   health_score_raw (2025 + 2010), threat_level_raw (trends)")
    print()
    print("3️⃣ COMPONENT OUTLETS: Provide all time periods")
    print("   microplastics_2003_raw, microplastics_2010_raw")
    print()
    print("4️⃣ TREND ANALYSIS: Calculate temporal relationships")
    print("   warming trends, pollution acceleration, ice loss")
    print()
    print("🎯 RESULT: Current ocean state + temporal dynamics")
    print("   → Most scientifically meaningful sonification")

if __name__ == "__main__":
    main()