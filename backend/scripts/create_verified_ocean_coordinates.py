#!/usr/bin/env python3
"""
Create a curated list of only VERIFIED ocean coordinates based on validation results.
This removes all coordinates that were detected as land and keeps only confirmed ocean points.
"""

import sys
sys.path.append('.')
from fixed_land_validation_server import ComprehensiveOceanDataServer

def create_verified_ocean_coordinates():
    """Create a verified list of ocean coordinates that pass land validation"""
    
    # Start with the coordinates that passed validation from the test
    verified_ocean_coordinates = [
        # ATLANTIC OCEAN - Verified Points (29 points)
        {"name": "North Atlantic Gyre", "lat": 35.0, "lng": -40.0},
        {"name": "North Atlantic Deep", "lat": 45.0, "lng": -35.0},
        {"name": "Sargasso Sea Central", "lat": 28.0, "lng": -55.0},
        {"name": "Labrador Sea", "lat": 58.0, "lng": -50.0},
        {"name": "North Atlantic Central", "lat": 50.0, "lng": -30.0},
        {"name": "Newfoundland Basin", "lat": 42.0, "lng": -45.0},
        {"name": "Azores Deep", "lat": 40.0, "lng": -25.0},
        {"name": "Madeira Abyssal Plain", "lat": 30.0, "lng": -20.0},
        {"name": "North American Basin", "lat": 38.0, "lng": -50.0},
        {"name": "European Basin", "lat": 48.0, "lng": -20.0},
        {"name": "North Atlantic Ridge", "lat": 55.0, "lng": -25.0},
        {"name": "Canary Basin", "lat": 25.0, "lng": -20.0},
        {"name": "Cape Verde Basin", "lat": 15.0, "lng": -25.0},
        {"name": "Mid-Atlantic Deep", "lat": -5.0, "lng": -25.0},
        {"name": "Equatorial Atlantic West", "lat": 0.0, "lng": -30.0},
        {"name": "Sierra Leone Basin", "lat": 8.0, "lng": -20.0},
        {"name": "Gambia Abyssal Plain", "lat": 12.0, "lng": -22.0},
        {"name": "Mid-Atlantic Ridge Equatorial", "lat": 0.0, "lng": -25.0},
        {"name": "South Atlantic Gyre", "lat": -30.0, "lng": -25.0},
        {"name": "Brazil Basin", "lat": -20.0, "lng": -30.0},
        {"name": "Cape Basin", "lat": -40.0, "lng": 5.0},
        {"name": "South African Basin", "lat": -45.0, "lng": 10.0},
        {"name": "Agulhas Basin", "lat": -38.0, "lng": 15.0},
        {"name": "Pernambuco Abyssal Plain", "lat": -10.0, "lng": -30.0},
        {"name": "Drake Passage Central", "lat": -58.0, "lng": -65.0},
        {"name": "South Atlantic Ridge", "lat": -45.0, "lng": -20.0},
        {"name": "Meteor Deep", "lat": -52.0, "lng": -15.0},
        {"name": "Tristan da Cunha Deep", "lat": -40.0, "lng": -10.0},
        {"name": "Gough Island Deep", "lat": -42.0, "lng": -8.0},
        
        # PACIFIC OCEAN - Verified Points (35 points)
        {"name": "Eastern Pacific", "lat": 25.0, "lng": -120.0},
        {"name": "Central Pacific", "lat": 20.0, "lng": -160.0},
        {"name": "Bering Sea Deep", "lat": 58.0, "lng": -175.0},
        {"name": "Molokai Deep", "lat": 25.0, "lng": -155.0},
        {"name": "Hawaiian Deep", "lat": 20.0, "lng": -155.0},
        {"name": "Clipperton Deep", "lat": 10.0, "lng": -105.0},
        {"name": "Equatorial Pacific West", "lat": 0.0, "lng": -170.0},
        {"name": "Equatorial Pacific Central", "lat": 0.0, "lng": -140.0},
        {"name": "Equatorial Pacific East", "lat": 0.0, "lng": -110.0},
        {"name": "Galapagos Deep", "lat": -2.0, "lng": -95.0},
        {"name": "Ecuador Deep", "lat": -5.0, "lng": -85.0},
        {"name": "ITCZ Pacific", "lat": 8.0, "lng": -130.0},
        {"name": "Doldrums Deep", "lat": 5.0, "lng": -120.0},
        {"name": "Christmas Island Deep", "lat": 2.0, "lng": -157.0},
        {"name": "Line Islands Deep", "lat": 5.0, "lng": -160.0},
        {"name": "Phoenix Deep", "lat": -5.0, "lng": -170.0},
        {"name": "South Pacific Gyre", "lat": -25.0, "lng": -120.0},
        {"name": "Southwest Pacific", "lat": -35.0, "lng": -170.0},
        {"name": "Chile Basin", "lat": -40.0, "lng": -90.0},
        {"name": "Peru Basin", "lat": -15.0, "lng": -85.0},
        {"name": "Easter Island Deep", "lat": -25.0, "lng": -110.0},
        {"name": "Samoa Deep", "lat": -15.0, "lng": -170.0},
        {"name": "Fiji Deep", "lat": -20.0, "lng": 175.0},
        {"name": "Tonga Deep", "lat": -25.0, "lng": -175.0},
        {"name": "Vanuatu Deep", "lat": -18.0, "lng": 168.0},
        {"name": "New Caledonia Deep", "lat": -25.0, "lng": 165.0},
        {"name": "Tasman Sea Central", "lat": -40.0, "lng": 160.0},
        {"name": "Chatham Deep", "lat": -45.0, "lng": -175.0},
        {"name": "Campbell Deep", "lat": -55.0, "lng": 170.0},
        {"name": "Macquarie Deep", "lat": -55.0, "lng": 160.0},
        {"name": "South Pacific Ridge", "lat": -50.0, "lng": -110.0},
        {"name": "East Pacific Rise", "lat": -30.0, "lng": -105.0},
        {"name": "Tahiti Deep", "lat": -20.0, "lng": -150.0},
        {"name": "Marquesas Deep", "lat": -10.0, "lng": -140.0},
        {"name": "Society Deep", "lat": -18.0, "lng": -155.0},
        {"name": "Cook Deep", "lat": -22.0, "lng": -160.0},
        {"name": "Austral Deep", "lat": -25.0, "lng": -145.0},
        {"name": "Tuamotu Deep", "lat": -15.0, "lng": -145.0},
        {"name": "Pitcairn Deep", "lat": -25.0, "lng": -130.0},
        
        # INDIAN OCEAN - Verified Points (22 points)
        {"name": "Central Indian Ocean", "lat": -10.0, "lng": 80.0},
        {"name": "Mid-Indian Ocean", "lat": 5.0, "lng": 75.0},
        {"name": "Southwest Indian Ocean", "lat": -30.0, "lng": 55.0},
        {"name": "Maldives Deep", "lat": 2.0, "lng": 73.0},
        {"name": "Chagos Deep", "lat": -8.0, "lng": 72.0},
        {"name": "Mascarene Deep", "lat": -20.0, "lng": 60.0},
        {"name": "Seychelles Deep", "lat": -8.0, "lng": 55.0},
        {"name": "Carlsberg Ridge", "lat": 5.0, "lng": 65.0},
        {"name": "Central Indian Ridge", "lat": -15.0, "lng": 70.0},
        {"name": "Rodriguez Deep", "lat": -22.0, "lng": 65.0},
        {"name": "Mauritius Deep", "lat": -25.0, "lng": 58.0},
        {"name": "Reunion Deep", "lat": -25.0, "lng": 55.0},
        {"name": "Agulhas Deep", "lat": -40.0, "lng": 25.0},
        {"name": "Crozet Deep", "lat": -45.0, "lng": 50.0},
        {"name": "Kerguelen Deep", "lat": -50.0, "lng": 70.0},
        {"name": "Heard Deep", "lat": -55.0, "lng": 75.0},
        {"name": "Amsterdam Deep", "lat": -40.0, "lng": 80.0},
        {"name": "St. Paul Deep", "lat": -42.0, "lng": 78.0},
        {"name": "Perth Deep", "lat": -35.0, "lng": 105.0},
        {"name": "Diamantina Deep", "lat": -40.0, "lng": 100.0},
        {"name": "Broken Ridge Deep", "lat": -30.0, "lng": 95.0},
        {"name": "Ninety East Ridge", "lat": -20.0, "lng": 90.0},
        {"name": "Wharton Deep", "lat": -15.0, "lng": 100.0},
        {"name": "Java Deep", "lat": -12.0, "lng": 105.0},
        {"name": "Christmas Island Basin", "lat": -15.0, "lng": 105.0},
        {"name": "Cocos Deep", "lat": -15.0, "lng": 95.0},
        {"name": "Sri Lanka Deep", "lat": 5.0, "lng": 82.0},
        {"name": "South Indian Basin", "lat": -50.0, "lng": 90.0},
        
        # SOUTHERN OCEAN - Verified Points (19 points)
        {"name": "Drake Passage Deep", "lat": -58.0, "lng": -65.0},
        {"name": "Tasman Deep Southern", "lat": -50.0, "lng": 160.0},
        {"name": "Ross Sea Central", "lat": -75.0, "lng": 180.0},
        {"name": "Weddell Sea Deep", "lat": -70.0, "lng": -45.0},
        {"name": "Bellingshausen Sea", "lat": -72.0, "lng": -75.0},
        {"name": "Amundsen Sea", "lat": -73.0, "lng": -110.0},
        {"name": "Ross Ice Shelf Deep", "lat": -78.0, "lng": 175.0},
        {"name": "Marie Byrd Land Deep", "lat": -75.0, "lng": -125.0},
        {"name": "Enderby Deep", "lat": -65.0, "lng": 50.0},
        {"name": "Mac Robertson Deep", "lat": -67.0, "lng": 65.0},
        {"name": "Princess Elizabeth Deep", "lat": -68.0, "lng": 80.0},
        {"name": "Wilhelm II Deep", "lat": -66.0, "lng": 95.0},
        {"name": "Queen Mary Deep", "lat": -67.0, "lng": 100.0},
        {"name": "Wilkes Deep", "lat": -66.0, "lng": 110.0},
        {"name": "Adelie Deep", "lat": -67.0, "lng": 140.0},
        {"name": "George V Deep", "lat": -67.0, "lng": 150.0},
        {"name": "Oates Deep", "lat": -67.0, "lng": 155.0},
        {"name": "Victoria Deep", "lat": -72.0, "lng": 165.0},
        {"name": "Antarctic Peninsula Deep", "lat": -70.0, "lng": -60.0},
        
        # ARCTIC OCEAN - Verified Points (5 points)
        {"name": "Beaufort Sea Deep", "lat": 75.0, "lng": -135.0},
        {"name": "Canada Basin", "lat": 80.0, "lng": -125.0},
        {"name": "Makarov Basin", "lat": 85.0, "lng": 160.0},
        {"name": "Fram Strait Deep", "lat": 80.0, "lng": 0.0},
        {"name": "Lomonosov Ridge", "lat": 85.0, "lng": 90.0},
        
        # Additional verified deep ocean points to reach ~150 total
        {"name": "Bermuda Deep", "lat": 30.0, "lng": -65.0},
        {"name": "Blake Plateau Deep", "lat": 30.0, "lng": -75.0},
        {"name": "Hatteras Deep Atlantic", "lat": 35.0, "lng": -70.0},
        {"name": "Caribbean Deep", "lat": 15.0, "lng": -70.0},
        {"name": "Venezuelan Basin", "lat": 12.0, "lng": -65.0},
        {"name": "Colombian Basin", "lat": 10.0, "lng": -75.0},
        {"name": "Cayman Deep", "lat": 17.0, "lng": -80.0},
        {"name": "Yucatan Deep", "lat": 20.0, "lng": -85.0},
        {"name": "Gulf of Mexico Deep", "lat": 25.0, "lng": -90.0},
        {"name": "Florida Deep", "lat": 24.0, "lng": -80.0},
        {"name": "Puerto Rico Deep", "lat": 18.0, "lng": -67.0},
        {"name": "Antilles Deep", "lat": 15.0, "lng": -60.0},
        {"name": "Barbados Deep", "lat": 12.0, "lng": -58.0},
        {"name": "Trinidad Deep", "lat": 8.0, "lng": -60.0},
        {"name": "Amazon Deep", "lat": 5.0, "lng": -50.0},
        {"name": "Guiana Deep", "lat": 8.0, "lng": -55.0},
        {"name": "Orinoco Deep", "lat": 10.0, "lng": -62.0},
        {"name": "North Pacific Central", "lat": 40.0, "lng": -150.0},
        {"name": "Northeast Pacific Deep", "lat": 50.0, "lng": -140.0},
        {"name": "Northwest Pacific Central", "lat": 40.0, "lng": 160.0},
        {"name": "Sea of Japan Deep", "lat": 40.0, "lng": 135.0},
        {"name": "Coral Triangle Deep", "lat": -5.0, "lng": 130.0},
        {"name": "Banda Sea Deep", "lat": -6.0, "lng": 128.0},
        {"name": "Celebes Sea Deep", "lat": 4.0, "lng": 123.0},
        {"name": "Sulu Sea Deep", "lat": 8.0, "lng": 120.0},
        {"name": "South China Sea Deep", "lat": 15.0, "lng": 115.0},
        {"name": "Philippine Sea Deep", "lat": 20.0, "lng": 135.0},
        {"name": "East China Sea Deep", "lat": 30.0, "lng": 125.0},
        {"name": "Yellow Sea Deep", "lat": 35.0, "lng": 123.0}
    ]
    
    # Validate all coordinates to ensure they are ocean
    server = ComprehensiveOceanDataServer()
    final_verified_coordinates = []
    
    print("🧪 Validating Curated Ocean Coordinates")
    print("=" * 60)
    
    for coord in verified_ocean_coordinates:
        is_ocean, confidence, location_type = server.is_over_ocean(coord["lat"], coord["lng"])
        if is_ocean:
            final_verified_coordinates.append(coord)
            print(f"✅ {coord['name']:<30} | {coord['lat']:7.1f}°, {coord['lng']:7.1f}°")
        else:
            print(f"❌ {coord['name']:<30} | {coord['lat']:7.1f}°, {coord['lng']:7.1f}° | REJECTED: {location_type}")
    
    print("=" * 60)
    print(f"✅ Validated {len(final_verified_coordinates)} ocean coordinates")
    
    return final_verified_coordinates

def save_verified_coordinates():
    """Save the verified ocean coordinates"""
    coordinates = create_verified_ocean_coordinates()
    
    # Save as Python module
    python_file = "/Users/marco/Documents/PROJECTS_2025/Panta-rhei/panta-rhei-data-map/verified_ocean_coordinates.py"
    with open(python_file, 'w') as f:
        f.write('#!/usr/bin/env python3\n')
        f.write('"""Verified ocean coordinates that pass land validation"""\n\n')
        f.write(f'# Total verified coordinates: {len(coordinates)}\n')
        f.write('# All coordinates have been validated as ocean points\n\n')
        f.write('VERIFIED_OCEAN_COORDINATES = [\n')
        for coord in coordinates:
            f.write(f'    {{"name": "{coord["name"]}", "lat": {coord["lat"]}, "lng": {coord["lng"]}}},\n')
        f.write(']\n')
    
    print(f"\\n📄 Saved {len(coordinates)} verified coordinates to: {python_file}")
    return coordinates

if __name__ == "__main__":
    save_verified_coordinates()