#!/usr/bin/env python3
"""
Ultra-scalable ocean coordinate generator that can produce 10,000+ verified points.
Uses efficient caching and batch processing for maximum performance.
"""

import sys
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.append('.')
from fixed_land_validation_server import ComprehensiveOceanDataServer

class UltraScalableOceanGenerator:
    def __init__(self):
        self.server = ComprehensiveOceanDataServer()
        self.cache = {}  # Cache validation results
        
    def is_ocean_cached(self, lat, lng):
        """Cached ocean validation for performance"""
        key = f"{lat:.2f},{lng:.2f}"  # Round to reduce cache size
        if key not in self.cache:
            is_ocean, confidence, location_type = self.server.is_over_ocean(lat, lng)
            self.cache[key] = (is_ocean, confidence, location_type)
        return self.cache[key]
    
    def generate_ocean_batch(self, region, batch_size=100):
        """Generate a batch of ocean coordinates for a region"""
        coordinates = []
        attempts = 0
        max_attempts = batch_size * 20
        
        while len(coordinates) < batch_size and attempts < max_attempts:
            attempts += 1
            
            # Generate random point in region
            lat = random.uniform(region['lat_min'], region['lat_max'])
            lng = random.uniform(region['lng_min'], region['lng_max'])
            
            # Keep within global bounds
            lat = max(-80, min(80, lat))
            lng = max(-180, min(180, lng))
            
            is_ocean, confidence, location_type = self.is_ocean_cached(lat, lng)
            
            if is_ocean:
                coordinates.append({
                    "name": f"{region['name']} Point {len(coordinates)+1:04d}",
                    "lat": round(lat, 4),
                    "lng": round(lng, 4),
                    "region": region['name'],
                    "depth_category": location_type
                })
        
        return coordinates
    
    def generate_massive_coordinates(self, target_count=10000):
        """Generate massive number of ocean coordinates"""
        
        print(f"🌊 Ultra-Scalable Ocean Generator")
        print(f"🎯 Target: {target_count:,} verified ocean coordinates")
        print("=" * 60)
        
        # Define ocean-rich regions with high ocean probability
        ocean_regions = [
            # Large ocean basins
            {"name": "North Atlantic Basin", "lat_min": 30, "lat_max": 65, "lng_min": -70, "lng_max": -10, "priority": 1.0},
            {"name": "South Atlantic Basin", "lat_min": -50, "lat_max": -10, "lng_min": -40, "lng_max": 20, "priority": 1.0},
            {"name": "North Pacific Basin", "lat_min": 20, "lat_max": 60, "lng_min": 140, "lng_max": -110, "priority": 1.2},
            {"name": "Central Pacific Basin", "lat_min": -20, "lat_max": 20, "lng_min": 120, "lng_max": -80, "priority": 1.5},
            {"name": "South Pacific Basin", "lat_min": -50, "lat_max": -20, "lng_min": 120, "lng_max": -70, "priority": 1.2},
            {"name": "Indian Ocean Basin", "lat_min": -40, "lat_max": 20, "lng_min": 40, "lng_max": 120, "priority": 1.0},
            {"name": "Southern Ocean", "lat_min": -70, "lat_max": -40, "lng_min": -180, "lng_max": 180, "priority": 0.8},
            {"name": "Arctic Ocean", "lat_min": 70, "lat_max": 85, "lng_min": -180, "lng_max": 180, "priority": 0.5},
            
            # Specific seas and deep water areas
            {"name": "Caribbean Sea", "lat_min": 10, "lat_max": 25, "lng_min": -85, "lng_max": -60, "priority": 0.6},
            {"name": "Mediterranean Sea", "lat_min": 30, "lat_max": 45, "lng_min": -5, "lng_max": 40, "priority": 0.4},
            {"name": "Gulf of Mexico", "lat_min": 18, "lat_max": 30, "lng_min": -97, "lng_max": -80, "priority": 0.5},
            {"name": "Sea of Japan", "lat_min": 30, "lat_max": 50, "lng_min": 125, "lng_max": 145, "priority": 0.7},
            {"name": "Bering Sea", "lat_min": 50, "lat_max": 65, "lng_min": 160, "lng_max": -160, "priority": 0.8},
            {"name": "Coral Sea", "lat_min": -25, "lat_max": -10, "lng_min": 145, "lng_max": 165, "priority": 0.8},
            {"name": "Tasman Sea", "lat_min": -45, "lat_max": -25, "lng_min": 150, "lng_max": 170, "priority": 0.8},
        ]
        
        # Calculate coordinates per region based on priority
        total_priority = sum(r['priority'] for r in ocean_regions)
        
        all_coordinates = []
        batch_size = 100
        
        start_time = time.time()
        
        # Use parallel processing for better performance
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_region = {}
            
            for region in ocean_regions:
                region_target = int((region['priority'] / total_priority) * target_count)
                num_batches = max(1, region_target // batch_size)
                
                print(f"🗺️ {region['name']}: targeting {region_target} coordinates in {num_batches} batches")
                
                # Submit batches for parallel processing
                for batch_idx in range(num_batches):
                    future = executor.submit(self.generate_ocean_batch, region, batch_size)
                    future_to_region[future] = (region, batch_idx)
            
            # Collect results
            for future in as_completed(future_to_region):
                region, batch_idx = future_to_region[future]
                try:
                    batch_coords = future.result()
                    all_coordinates.extend(batch_coords)
                    
                    if len(all_coordinates) % 500 == 0:
                        elapsed = time.time() - start_time
                        rate = len(all_coordinates) / elapsed
                        print(f"  ✅ Progress: {len(all_coordinates):,} coordinates ({rate:.1f}/sec)")
                    
                    # Stop if we've reached our target
                    if len(all_coordinates) >= target_count:
                        break
                        
                except Exception as e:
                    print(f"  ❌ Batch failed for {region['name']}: {e}")
        
        # Trim to exact target if we exceeded
        if len(all_coordinates) > target_count:
            all_coordinates = random.sample(all_coordinates, target_count)
        
        elapsed = time.time() - start_time
        print(f"\\n⏱️ Generation completed in {elapsed:.1f} seconds")
        print(f"📊 Average rate: {len(all_coordinates)/elapsed:.1f} coordinates/second")
        print(f"🎯 Final count: {len(all_coordinates):,} verified ocean coordinates")
        
        return all_coordinates
    
    def save_ultra_coordinates(self, target_count=10000):
        """Generate and save ultra-scale coordinate database"""
        
        coordinates = self.generate_massive_coordinates(target_count)
        
        # Save files with efficient formats
        base_name = f"ultra_ocean_coordinates_{len(coordinates)}"
        
        # Compressed JSON for storage
        json_file = f"/Users/marco/Documents/PROJECTS_2025/Panta-rhei/panta-rhei-data-map/{base_name}.json"
        with open(json_file, 'w') as f:
            json.dump(coordinates, f, separators=(',', ':'))  # Compact format
        
        # Python module (only for smaller datasets due to file size)
        if len(coordinates) <= 5000:
            python_file = f"/Users/marco/Documents/PROJECTS_2025/Panta-rhei/panta-rhei-data-map/{base_name}.py"
            with open(python_file, 'w') as f:
                f.write('#!/usr/bin/env python3\\n')
                f.write(f'"""Ultra-scale ocean coordinates - {len(coordinates):,} verified points""\"\\n\\n')
                f.write(f'ULTRA_OCEAN_COORDINATES = [\\n')
                for coord in coordinates:
                    f.write(f'    {{"name": "{coord["name"]}", "lat": {coord["lat"]}, "lng": {coord["lng"]}}},\\n')
                f.write(']\\n')
        
        # Frontend optimized versions
        for size in [100, 500, 1000]:
            if len(coordinates) >= size:
                frontend_coords = random.sample(coordinates, size)
                frontend_file = f"/Users/marco/Documents/PROJECTS_2025/Panta-rhei/panta-rhei-data-map/frontend_ultra_{size}.js"
                with open(frontend_file, 'w') as f:
                    f.write(f'// Ultra-optimized ocean coordinates - {size} points\\n')
                    f.write(f'// Selected from {len(coordinates):,} total verified coordinates\\n\\n')
                    f.write(f'export const ULTRA_OCEAN_COORDINATES_{size} = [\\n')
                    for coord in frontend_coords:
                        f.write(f'  {{ name: "{coord["name"]}", lat: {coord["lat"]}, lng: {coord["lng"]} }},\\n')
                    f.write('];\\n')
        
        # Statistics
        region_stats = {}
        for coord in coordinates:
            region = coord.get("region", "Unknown")
            region_stats[region] = region_stats.get(region, 0) + 1
        
        print(f"\\n📊 Ultra-Scale Database Statistics:")
        print(f"   • Total coordinates: {len(coordinates):,}")
        print(f"   • Ocean regions: {len(region_stats)}")
        print(f"   • Cache hits: {len(self.cache):,}")
        print(f"   • Average per region: {len(coordinates)/len(region_stats):.0f}")
        
        print(f"\\n💾 Files Generated:")
        print(f"   📄 Compressed JSON: {json_file}")
        if len(coordinates) <= 5000:
            print(f"   🐍 Python module: {python_file}")
        print(f"   ⚡ Frontend variants: 100, 500, 1000 point versions")
        
        print(f"\\n🚀 **ULTIMATE SCALING ACHIEVED:**")
        print(f"   • Original system: 26 coordinates")
        print(f"   • Enhanced system: 120 coordinates")  
        print(f"   • Current system: {len(coordinates):,} coordinates")
        print(f"   • Scaling factor: {len(coordinates)/26:.0f}x increase")
        print(f"   • Performance: {len(coordinates)/len(self.cache):.1f} coords per unique validation")
        
        return coordinates

def main():
    """Main function for ultra-scalable coordinate generation"""
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    
    generator = UltraScalableOceanGenerator()
    coordinates = generator.save_ultra_coordinates(target)
    
    print(f"\\n✅ Ultra-scalable ocean coordinate generation complete!")
    print(f"Generated {len(coordinates):,} verified ocean coordinates.")

if __name__ == "__main__":
    main()