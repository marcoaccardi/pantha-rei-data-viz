#!/usr/bin/env python3
"""
Generate thousands of verified ocean coordinates using systematic grid sampling.
This approach can scale to 10,000+ verified ocean coordinates.
"""

import sys
import json
sys.path.append('.')
from fixed_land_validation_server import ComprehensiveOceanDataServer

def generate_systematic_ocean_grid(target_count=5000):
    """Generate thousands of ocean coordinates using systematic grid sampling"""
    
    server = ComprehensiveOceanDataServer()
    verified_coordinates = []
    
    print(f"🌊 Generating {target_count} verified ocean coordinates using systematic grid sampling")
    print("=" * 80)
    
    # Define ocean-rich regions with their bounding boxes
    ocean_regions = [
        # Atlantic Ocean Regions
        {"name": "North Atlantic", "lat_min": 20, "lat_max": 70, "lng_min": -80, "lng_max": -10, "density": 0.8},
        {"name": "Tropical Atlantic", "lat_min": -10, "lat_max": 20, "lng_min": -60, "lng_max": -10, "density": 0.7},
        {"name": "South Atlantic", "lat_min": -60, "lat_max": -10, "lng_min": -50, "lng_max": 20, "density": 0.8},
        
        # Pacific Ocean Regions
        {"name": "North Pacific", "lat_min": 20, "lat_max": 65, "lng_min": 120, "lng_max": -120, "density": 0.9},
        {"name": "Central Pacific", "lat_min": -20, "lat_max": 20, "lng_min": 120, "lng_max": -80, "density": 0.9},
        {"name": "South Pacific", "lat_min": -60, "lat_max": -20, "lng_min": 120, "lng_max": -70, "density": 0.9},
        
        # Indian Ocean Regions
        {"name": "North Indian Ocean", "lat_min": 0, "lat_max": 25, "lng_min": 50, "lng_max": 100, "density": 0.7},
        {"name": "Central Indian Ocean", "lat_min": -40, "lat_max": 0, "lng_min": 40, "lng_max": 120, "density": 0.8},
        {"name": "Southern Indian Ocean", "lat_min": -60, "lat_max": -40, "lng_min": 20, "lng_max": 140, "density": 0.8},
        
        # Southern Ocean
        {"name": "Southern Ocean Atlantic", "lat_min": -75, "lat_max": -50, "lng_min": -60, "lng_max": 60, "density": 0.6},
        {"name": "Southern Ocean Pacific", "lat_min": -75, "lat_max": -50, "lng_min": 120, "lng_max": -60, "density": 0.6},
        {"name": "Southern Ocean Indian", "lat_min": -75, "lat_max": -50, "lng_min": 60, "lng_max": 120, "density": 0.6},
        
        # Arctic Ocean (ice-free areas)
        {"name": "Arctic Ocean", "lat_min": 70, "lat_max": 85, "lng_min": -180, "lng_max": 180, "density": 0.3},
    ]
    
    # Calculate grid step size based on target count and region sizes
    total_area = sum((region["lat_max"] - region["lat_min"]) * 
                    (region["lng_max"] - region["lng_min"]) * region["density"] 
                    for region in ocean_regions)
    
    base_step = (total_area / target_count) ** 0.5
    
    # Generate coordinates for each region
    for region in ocean_regions:
        print(f"\\n🗺️ Processing {region['name']}...")
        
        # Adjust step size based on region density
        step_size = base_step / (region["density"] ** 0.5)
        
        lat_min, lat_max = float(region["lat_min"]), float(region["lat_max"])
        lng_min, lng_max = float(region["lng_min"]), float(region["lng_max"])
        
        # Handle longitude wraparound for Pacific regions
        if lng_max < lng_min:  # Crosses 180° meridian
            # Split into two parts
            lng_ranges = [(lng_min, 180.0), (-180.0, lng_max)]
        else:
            lng_ranges = [(lng_min, lng_max)]
        
        region_count = 0
        for lng_range in lng_ranges:
            lng_start, lng_end = lng_range
            
            lat = float(lat_min)
            while lat <= lat_max:
                lng = float(lng_start)
                while lng <= lng_end:
                    # Add small random offset to avoid grid artifacts
                    hash_lat = abs(hash(f"{lat}_{lng}")) % 100 - 50
                    hash_lng = abs(hash(f"{lng}_{lat}")) % 100 - 50
                    test_lat = float(lat + hash_lat / 100.0 * step_size * 0.5)
                    test_lng = float(lng + hash_lng / 100.0 * step_size * 0.5)
                    
                    # Keep within bounds
                    test_lat = max(-80.0, min(80.0, test_lat))
                    test_lng = max(-180.0, min(180.0, test_lng))
                    
                    # Test if it's ocean
                    is_ocean, confidence, location_type = server.is_over_ocean(test_lat, test_lng)
                    
                    if is_ocean:
                        # Generate descriptive name based on region and position
                        sub_region = ""
                        if lat > (lat_min + lat_max) / 2:
                            sub_region = "North"
                        else:
                            sub_region = "South"
                        
                        if lng > (lng_start + lng_end) / 2:
                            sub_region += " East"
                        else:
                            sub_region += " West"
                        
                        coord_name = f"{region['name']} {sub_region} {len(verified_coordinates)+1:04d}"
                        
                        verified_coordinates.append({
                            "name": coord_name,
                            "lat": round(test_lat, 4),
                            "lng": round(test_lng, 4),
                            "region": region["name"],
                            "depth_category": location_type
                        })
                        
                        region_count += 1
                        
                        if len(verified_coordinates) % 100 == 0:
                            print(f"  ✅ Generated {len(verified_coordinates)} coordinates...")
                        
                        if len(verified_coordinates) >= target_count:
                            break
                    
                    lng += float(step_size)
                
                if len(verified_coordinates) >= target_count:
                    break
                lat += float(step_size)
            
            if len(verified_coordinates) >= target_count:
                break
        
        print(f"  📍 {region['name']}: {region_count} coordinates")
        
        if len(verified_coordinates) >= target_count:
            break
    
    print("\\n" + "=" * 80)
    print(f"✅ Generated {len(verified_coordinates)} verified ocean coordinates")
    
    # Statistics by region
    region_stats = {}
    for coord in verified_coordinates:
        region = coord["region"]
        if region not in region_stats:
            region_stats[region] = 0
        region_stats[region] += 1
    
    print("\\n📊 Regional Distribution:")
    for region, count in sorted(region_stats.items()):
        percentage = (count / len(verified_coordinates)) * 100
        print(f"  • {region:<25}: {count:4d} points ({percentage:5.1f}%)")
    
    return verified_coordinates

def save_massive_coordinates(target_count=5000):
    """Generate and save massive ocean coordinate database"""
    
    coordinates = generate_systematic_ocean_grid(target_count)
    
    # Save as JSON for easy loading
    json_file = f"/Users/marco/Documents/PROJECTS_2025/Panta-rhei/panta-rhei-data-map/massive_ocean_coordinates_{len(coordinates)}.json"
    with open(json_file, 'w') as f:
        json.dump(coordinates, f, indent=2)
    
    # Save as Python module for direct import
    python_file = f"/Users/marco/Documents/PROJECTS_2025/Panta-rhei/panta-rhei-data-map/massive_ocean_coordinates_{len(coordinates)}.py"
    with open(python_file, 'w') as f:
        f.write('#!/usr/bin/env python3\\n')
        f.write(f'"""Massive verified ocean coordinates database - {len(coordinates)} points""\"\\n\\n')
        f.write(f'# Total coordinates: {len(coordinates)}\\n')
        f.write('# Generated using systematic grid sampling\\n')
        f.write('# All coordinates validated as ocean points\\n\\n')
        f.write(f'MASSIVE_OCEAN_COORDINATES = [\\n')
        for i, coord in enumerate(coordinates):
            f.write(f'    {{"name": "{coord["name"]}", "lat": {coord["lat"]}, "lng": {coord["lng"]}}},\\n')
            if i % 100 == 99:  # Add progress comment every 100 coordinates
                f.write(f'    # {i+1} coordinates loaded...\\n')
        f.write(']\\n\\n')
        f.write(f'# Regional distribution included {len(set(coord["region"] for coord in coordinates))} ocean regions\\n')
        f.write(f'# Grid-based systematic sampling ensures global coverage\\n')
    
    # Create optimized version for frontend (smaller subset)
    frontend_subset = coordinates[::max(1, len(coordinates)//500)]  # Max 500 for frontend
    frontend_file = f"/Users/marco/Documents/PROJECTS_2025/Panta-rhei/panta-rhei-data-map/frontend_ocean_coordinates_{len(frontend_subset)}.py"
    with open(frontend_file, 'w') as f:
        f.write('#!/usr/bin/env python3\\n')
        f.write(f'"""Frontend-optimized ocean coordinates - {len(frontend_subset)} points""\"\\n\\n')
        f.write(f'# Optimized subset of {len(coordinates)} total coordinates\\n')
        f.write('# Selected for global coverage and performance\\n\\n')
        f.write(f'FRONTEND_OCEAN_COORDINATES = [\\n')
        for coord in frontend_subset:
            f.write(f'    {{"name": "{coord["name"]}", "lat": {coord["lat"]}, "lng": {coord["lng"]}}},\\n')
        f.write(']\\n')
    
    print(f"\\n💾 Saved coordinate databases:")
    print(f"   📄 Full JSON: {json_file}")
    print(f"   🐍 Full Python: {python_file}")
    print(f"   ⚡ Frontend Optimized: {frontend_file}")
    print(f"\\n🎯 **SCALING ACHIEVED:**")
    print(f"   • Original: 26 coordinates")
    print(f"   • Previous: 120 coordinates") 
    print(f"   • Current: {len(coordinates)} coordinates ({len(coordinates)/26:.0f}x increase)")
    print(f"   • Frontend: {len(frontend_subset)} coordinates (optimized for performance)")
    
    return coordinates, frontend_subset

if __name__ == "__main__":
    import sys
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    print(f"🎯 Target: {target} verified ocean coordinates")
    save_massive_coordinates(target)