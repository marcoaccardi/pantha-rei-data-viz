#!/usr/bin/env python3
"""
Generate thousands of verified ocean coordinates using simplified systematic sampling.
"""

import sys
import json
import random
sys.path.append('.')
from fixed_land_validation_server import ComprehensiveOceanDataServer

def generate_massive_ocean_coordinates(target_count=1000):
    """Generate many ocean coordinates using simple grid + random sampling"""
    
    server = ComprehensiveOceanDataServer()
    verified_coordinates = []
    
    print(f"🌊 Generating {target_count} verified ocean coordinates")
    print("=" * 60)
    
    # Define high-density ocean regions (known to be mostly ocean)
    ocean_zones = [
        # Deep ocean areas with high ocean probability
        {"name": "North Atlantic Deep", "lat_center": 45, "lng_center": -35, "radius": 15},
        {"name": "South Atlantic Deep", "lat_center": -30, "lng_center": -25, "radius": 15},
        {"name": "North Pacific Deep", "lat_center": 35, "lng_center": -155, "radius": 20},
        {"name": "Central Pacific", "lat_center": 0, "lng_center": -160, "radius": 25},
        {"name": "South Pacific Deep", "lat_center": -25, "lng_center": -120, "radius": 20},
        {"name": "Indian Ocean Deep", "lat_center": -20, "lng_center": 80, "radius": 15},
        {"name": "Southern Ocean", "lat_center": -60, "lng_center": 0, "radius": 25},
        {"name": "Arctic Ocean", "lat_center": 80, "lng_center": 0, "radius": 10},
        # Add more specific regions
        {"name": "Sargasso Sea", "lat_center": 28, "lng_center": -55, "radius": 8},
        {"name": "Labrador Sea", "lat_center": 58, "lng_center": -50, "radius": 8},
        {"name": "Bering Sea", "lat_center": 58, "lng_center": -175, "radius": 8},
        {"name": "Coral Sea", "lat_center": -18, "lng_center": 155, "radius": 8},
        {"name": "Tasman Sea", "lat_center": -40, "lng_center": 160, "radius": 8},
        {"name": "Drake Passage", "lat_center": -58, "lng_center": -65, "radius": 6},
        {"name": "Equatorial Pacific", "lat_center": 0, "lng_center": -140, "radius": 12},
        {"name": "Caribbean Deep", "lat_center": 15, "lng_center": -75, "radius": 8},
        {"name": "Mediterranean Deep", "lat_center": 38, "lng_center": 15, "radius": 6},
        {"name": "Red Sea", "lat_center": 20, "lng_center": 38, "radius": 4},
        {"name": "Persian Gulf", "lat_center": 26, "lng_center": 52, "radius": 3},
    ]
    
    # Calculate how many coordinates per zone
    coords_per_zone = target_count // len(ocean_zones)
    
    for zone in ocean_zones:
        print(f"🗺️ Processing {zone['name']}...")
        zone_count = 0
        attempts = 0
        max_attempts = coords_per_zone * 10  # Allow up to 10x attempts per zone
        
        while zone_count < coords_per_zone and attempts < max_attempts:
            attempts += 1
            
            # Generate random point within zone radius
            angle = random.uniform(0, 2 * 3.14159)
            distance = random.uniform(0, zone['radius'])
            
            # Convert to lat/lng offset
            lat_offset = distance * 0.9 * random.uniform(-1, 1)  # Slight compression for latitude
            lng_offset = distance * random.uniform(-1, 1)
            
            test_lat = zone['lat_center'] + lat_offset
            test_lng = zone['lng_center'] + lng_offset
            
            # Keep within valid bounds
            test_lat = max(-80, min(80, test_lat))
            test_lng = max(-180, min(180, test_lng))
            
            # Test if it's ocean
            is_ocean, confidence, location_type = server.is_over_ocean(test_lat, test_lng)
            
            if is_ocean:
                coord_name = f"{zone['name']} Point {zone_count+1:03d}"
                
                verified_coordinates.append({
                    "name": coord_name,
                    "lat": round(test_lat, 4),
                    "lng": round(test_lng, 4),
                    "zone": zone["name"],
                    "depth_category": location_type
                })
                
                zone_count += 1
                
                if len(verified_coordinates) % 50 == 0:
                    print(f"  ✅ Total: {len(verified_coordinates)} coordinates...")
        
        print(f"  📍 {zone['name']}: {zone_count} coordinates")
    
    print("\\n" + "=" * 60)
    print(f"✅ Generated {len(verified_coordinates)} verified ocean coordinates")
    
    return verified_coordinates

def create_progressive_expansion(base_coords, target_count):
    """Create progressive expansion from base coordinates"""
    
    if target_count <= len(base_coords):
        return random.sample(base_coords, target_count)
    
    server = ComprehensiveOceanDataServer()
    expanded_coords = base_coords.copy()
    
    print(f"🔄 Expanding from {len(base_coords)} to {target_count} coordinates...")
    
    # Add variations around existing coordinates
    while len(expanded_coords) < target_count:
        base_coord = random.choice(base_coords)
        
        # Create variation
        lat_offset = random.uniform(-5, 5)
        lng_offset = random.uniform(-5, 5)
        
        new_lat = base_coord['lat'] + lat_offset
        new_lng = base_coord['lng'] + lng_offset
        
        # Keep in bounds
        new_lat = max(-80, min(80, new_lat))
        new_lng = max(-180, min(180, new_lng))
        
        # Test if ocean
        is_ocean, confidence, location_type = server.is_over_ocean(new_lat, new_lng)
        
        if is_ocean:
            new_name = f"Expanded {base_coord['name']} Var {len(expanded_coords)+1:04d}"
            expanded_coords.append({
                "name": new_name,
                "lat": round(new_lat, 4),
                "lng": round(new_lng, 4),
                "zone": f"Expansion of {base_coord.get('zone', 'Unknown')}",
                "depth_category": location_type
            })
            
            if len(expanded_coords) % 100 == 0:
                print(f"  📊 Progress: {len(expanded_coords)}/{target_count}")
    
    return expanded_coords

def save_scaled_coordinates(target_count=1000):
    """Generate and save scaled ocean coordinate database"""
    
    print(f"🎯 Target: {target_count} verified ocean coordinates\\n")
    
    if target_count <= 500:
        # Direct generation for smaller counts
        coordinates = generate_massive_ocean_coordinates(target_count)
    else:
        # Progressive expansion for larger counts
        base_coords = generate_massive_ocean_coordinates(500)
        coordinates = create_progressive_expansion(base_coords, target_count)
    
    # Save files
    json_file = f"/Users/marco/Documents/PROJECTS_2025/Panta-rhei/panta-rhei-data-map/ocean_coordinates_{len(coordinates)}.json"
    with open(json_file, 'w') as f:
        json.dump(coordinates, f, indent=2)
    
    python_file = f"/Users/marco/Documents/PROJECTS_2025/Panta-rhei/panta-rhei-data-map/ocean_coordinates_{len(coordinates)}.py"
    with open(python_file, 'w') as f:
        f.write('#!/usr/bin/env python3\\n')
        f.write(f'"""Ocean coordinates database - {len(coordinates)} verified points""\"\\n\\n')
        f.write(f'OCEAN_COORDINATES_{len(coordinates)} = [\\n')
        for coord in coordinates:
            f.write(f'    {{"name": "{coord["name"]}", "lat": {coord["lat"]}, "lng": {coord["lng"]}}},\\n')
        f.write(']\\n')
    
    # Create frontend-optimized version (max 1000 for performance)
    frontend_size = min(1000, len(coordinates))
    frontend_coords = random.sample(coordinates, frontend_size) if len(coordinates) > frontend_size else coordinates
    
    frontend_file = f"/Users/marco/Documents/PROJECTS_2025/Panta-rhei/panta-rhei-data-map/frontend_coordinates_{frontend_size}.js"
    with open(frontend_file, 'w') as f:
        f.write(f'// Frontend-optimized ocean coordinates - {frontend_size} points\\n')
        f.write(f'// Selected from {len(coordinates)} total verified coordinates\\n\\n')
        f.write(f'export const OCEAN_COORDINATES_{frontend_size} = [\\n')
        for coord in frontend_coords:
            f.write(f'  {{ name: "{coord["name"]}", lat: {coord["lat"]}, lng: {coord["lng"]} }},\\n')
        f.write('];\\n')
    
    # Statistics
    zone_stats = {}
    for coord in coordinates:
        zone = coord.get("zone", "Unknown")
        zone_stats[zone] = zone_stats.get(zone, 0) + 1
    
    print(f"\\n📊 Generated coordinate database:")
    print(f"   • Total coordinates: {len(coordinates)}")
    print(f"   • Ocean zones covered: {len(zone_stats)}")
    print(f"   • Average per zone: {len(coordinates)/len(zone_stats):.1f}")
    
    print(f"\\n💾 Files saved:")
    print(f"   📄 JSON: {json_file}")
    print(f"   🐍 Python: {python_file}")
    print(f"   ⚡ Frontend JS: {frontend_file}")
    
    print(f"\\n🎯 **SCALING COMPARISON:**")
    print(f"   • Original: 26 coordinates")
    print(f"   • Previous: 120 coordinates")
    print(f"   • Current: {len(coordinates)} coordinates")
    print(f"   • Increase: {len(coordinates)/26:.0f}x from original")
    print(f"   • Frontend optimized: {frontend_size} coordinates")
    
    return coordinates

if __name__ == "__main__":
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    save_scaled_coordinates(target)