#!/usr/bin/env python3
"""
NOAA Climate Data Globe Texture System - Main Entry Point
Minimal, production-ready system for generating Earth textures with real oceanographic data.

Usage:
    python main.py                    # Run enhanced climate data collection (default)
    python main.py --earth-only       # Generate only Earth textures
    python main.py --sst-only         # Generate only SST textures
    python main.py --validate         # Validate existing outputs
"""

import argparse
import sys
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.processors.earth_textures import EarthTextureProcessor
from src.processors.erddap_sst_processor import ERDDAPSSTProcessor
from src.processors.enhanced_climate_data import EnhancedClimateDataProcessor
from src.utils.validation import TextureValidator
from src.utils.file_ops import FileOperations
import config

class NOAATextureSystem:
    """Main NOAA Climate Data Globe Texture System."""
    
    def __init__(self):
        """Initialize the system with essential processors only."""
        self.earth_processor = EarthTextureProcessor()
        self.erddap_sst_processor = ERDDAPSSTProcessor()
        self.enhanced_climate_processor = EnhancedClimateDataProcessor()
        self.validator = TextureValidator()
        self.file_ops = FileOperations()
        
        print("🌍 NOAA CLIMATE DATA GLOBE TEXTURE SYSTEM")
        print("=" * 80)
        print("🎯 Real NASA Earth + NOAA OISST Data → React Three Fiber Textures")
        print(f"🔧 Version: {config.SYSTEM_CONFIG['version']}")
        print("=" * 80)
    
    def generate_random_location_and_date(self) -> tuple[str, str]:
        """Generate random coordinates and date for data collection."""
        
        # Generate random coordinates (avoiding extreme polar regions for better data availability)
        lat = random.uniform(-75, 75)  # Avoid extreme polar regions
        lon = random.uniform(-180, 180)
        
        # Generate random date within the last year, but ensure it's not in the future
        # Most marine APIs only have data up to a few days ago
        end_date = datetime.now() - timedelta(days=7)  # 7 days ago to account for data lag
        start_date = end_date - timedelta(days=365)
        random_days = random.randint(0, 358)  # 365 - 7 days lag
        random_date = start_date + timedelta(days=random_days)
        
        coordinates = f"{lat:.4f},{lon:.4f}"
        date_str = random_date.strftime('%Y-%m-%d')
        
        return coordinates, date_str
    
    def print_climate_data_report(self, climate_data, csv_file: Path):
        """Print a well-formatted report of the collected climate data."""
        
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE CLIMATE DATA REPORT")
        print("=" * 80)
        
        # Location and metadata
        print(f"🌍 Location: {climate_data.latitude:.4f}°, {climate_data.longitude:.4f}°")
        print(f"📅 Date: {climate_data.date}")
        print(f"🌡️ Climate Zone: {climate_data.climate_zone.title()}")
        print(f"🏷️ Weather Labels: {', '.join(climate_data.weather_labels)}")
        print(f"📊 Overall Confidence: {climate_data.metadata.get('overall_confidence', 0):.1%}")
        print()
        
        # Current Weather Data
        if climate_data.current_weather:
            print("📡 CURRENT WEATHER CONDITIONS")
            print("-" * 40)
            
            key_params = ['temperature', 'wind_speed', 'wind_direction', 'barometric_pressure', 'relative_humidity', 'visibility']
            for param in key_params:
                data = climate_data.current_weather.get(param, {})
                if data and isinstance(data, dict) and data.get('value') is not None:
                    value = data['value']
                    unit = data.get('unit', '')
                    quality = data.get('quality_control', 'Unknown')
                    
                    # Format the output nicely
                    if param == 'temperature':
                        print(f"  🌡️  Temperature: {value:.1f}°C (Quality: {quality})")
                    elif param == 'wind_speed':
                        print(f"  💨 Wind Speed: {value:.1f} {unit} (Quality: {quality})")
                    elif param == 'wind_direction':
                        print(f"  🧭 Wind Direction: {value:.0f}° (Quality: {quality})")
                    elif param == 'barometric_pressure':
                        print(f"  📊 Pressure: {value:.0f} Pa (Quality: {quality})")
                    elif param == 'relative_humidity':
                        print(f"  💧 Humidity: {value:.1f}% (Quality: {quality})")
                    elif param == 'visibility':
                        print(f"  👁️  Visibility: {value/1000:.1f} km (Quality: {quality})")
            print()
        
        # Historical Climate Estimates
        if climate_data.historical_climate and 'estimated_temperature' in climate_data.historical_climate:
            print("📊 HISTORICAL CLIMATE DATA")
            print("-" * 40)
            temp_data = climate_data.historical_climate['estimated_temperature']
            print(f"  📈 Average Temperature: {temp_data.get('average', 'N/A'):.1f}°C")
            print(f"  🔽 Minimum Temperature: {temp_data.get('minimum', 'N/A'):.1f}°C")
            print(f"  🔼 Maximum Temperature: {temp_data.get('maximum', 'N/A'):.1f}°C")
            
            if 'estimated_precipitation' in climate_data.historical_climate:
                precip_data = climate_data.historical_climate['estimated_precipitation']
                print(f"  🌧️  Monthly Precipitation: {precip_data.get('monthly_total', 'N/A'):.1f} mm")
            print()
        
        # Gridded Analysis Data
        if climate_data.gridded_data and 'variables' in climate_data.gridded_data:
            print("🗺️ GRIDDED ANALYSIS DATA")
            print("-" * 40)
            variables = climate_data.gridded_data['variables']
            
            if 'sea_surface_temperature' in variables:
                print(f"  🌊 Sea Surface Temp: {variables['sea_surface_temperature']:.1f}°C")
            if 'land_surface_temperature' in variables:
                print(f"  🏔️  Land Surface Temp: {variables['land_surface_temperature']:.1f}°C")
            if 'precipitation_rate' in variables:
                print(f"  ☔ Precipitation Rate: {variables['precipitation_rate']:.2f} mm/day")
            if 'surface_pressure' in variables:
                print(f"  📊 Surface Pressure: {variables['surface_pressure']:.1f} hPa")
            print()
        
        # Coral Bleaching Data
        if hasattr(climate_data, 'coral_bleaching_data') and climate_data.coral_bleaching_data:
            print("🪸 CORAL REEF CONDITIONS")
            print("-" * 40)
            coral_data = climate_data.coral_bleaching_data
            
            # Show available coral reef parameters
            for param, data in coral_data.items():
                if isinstance(data, dict) and 'value' in data and data['value'] is not None:
                    value = data['value']
                    units = data.get('units', '')
                    if param == 'CRW_SST' or 'sst' in param.lower():
                        print(f"  🌡️ Sea Surface Temp: {value:.1f}°C")
                    elif param == 'CRW_DHW' or 'dhw' in param.lower():
                        print(f"  🔥 Degree Heating Weeks: {value:.1f} DHW")
                    elif param == 'CRW_BAA' or 'baa' in param.lower():
                        print(f"  ⚠️ Bleaching Alert: Level {int(value)}")
                    elif 'chlorophyll' in param.lower() or 'chl' in param.lower():
                        print(f"  🌿 Chlorophyll: {value:.2f} mg/m³")
            
            # Show risk assessment if available
            if 'risk_assessment' in coral_data:
                risk = coral_data['risk_assessment']
                overall_risk = risk.get('overall_risk', 'unknown')
                print(f"  🚨 Overall Risk: {overall_risk.title()}")
            print()
        
        # Wave Conditions
        if hasattr(climate_data, 'wave_data') and climate_data.wave_data:
            print("🌊 WAVE CONDITIONS")
            print("-" * 40)
            wave_data = climate_data.wave_data
            
            # Show available wave parameters
            for param, data in wave_data.items():
                if isinstance(data, dict) and 'value' in data and data['value'] is not None:
                    value = data['value']
                    if param == 'Thgt' or 'wave_height' in param.lower():
                        print(f"  🌊 Wave Height: {value:.1f} m")
                    elif param == 'Tper' or 'period' in param.lower():
                        print(f"  ⏱️ Wave Period: {value:.1f} s")
                    elif param == 'Tdir' or 'direction' in param.lower():
                        print(f"  🧭 Wave Direction: {value:.0f}°")
            
            # Show wave analysis if available
            if 'wave_analysis' in wave_data:
                analysis = wave_data['wave_analysis']
                sea_state = analysis.get('sea_state', 'unknown')
                print(f"  📊 Sea State: {sea_state.title()}")
            print()
        
        # Ocean Currents
        if hasattr(climate_data, 'ocean_currents') and climate_data.ocean_currents:
            print("🌊 OCEAN CURRENTS")
            print("-" * 40)
            currents_data = climate_data.ocean_currents
            
            # Show available current parameters
            for param, data in currents_data.items():
                if isinstance(data, dict) and 'value' in data and data['value'] is not None:
                    value = data['value']
                    if param in ['u', 'water_u']:
                        print(f"  ➡️ Eastward Current: {value:.2f} m/s")
                    elif param in ['v', 'water_v']:
                        print(f"  ⬆️ Northward Current: {value:.2f} m/s")
            
            # Show current analysis if available
            if 'current_analysis' in currents_data:
                analysis = currents_data['current_analysis']
                speed = analysis.get('current_speed')
                direction = analysis.get('current_direction')
                if speed is not None:
                    print(f"  🌊 Current Speed: {speed:.2f} m/s")
                if direction is not None:
                    print(f"  🧭 Current Direction: {direction:.0f}°")
            print()
        
        # Marine Biogeochemistry
        if hasattr(climate_data, 'marine_biogeochemistry') and climate_data.marine_biogeochemistry:
            print("🧪 MARINE BIOGEOCHEMISTRY")
            print("-" * 40)
            bio_data = climate_data.marine_biogeochemistry
            
            # Show available biogeochemical parameters
            for param, data in bio_data.items():
                if isinstance(data, dict) and 'value' in data and data['value'] is not None:
                    value = data['value']
                    units = data.get('units', '')
                    if 'chl' in param.lower() or 'chlorophyll' in param.lower():
                        print(f"  🌿 Chlorophyll-a: {value:.2f} mg/m³")
                    elif 'ph' in param.lower():
                        print(f"  🔬 Ocean pH: {value:.2f}")
                    elif 'o2' in param.lower() or 'oxygen' in param.lower():
                        print(f"  💨 Dissolved Oxygen: {value:.1f} mmol/m³")
                    elif 'no3' in param.lower() or 'nitrate' in param.lower():
                        print(f"  🧪 Nitrate: {value:.1f} mmol/m³")
            
            # Show ecosystem analysis if available
            if 'ecosystem_analysis' in bio_data:
                analysis = bio_data['ecosystem_analysis']
                productivity = analysis.get('productivity_level', 'unknown')
                health = analysis.get('ecosystem_health', 'unknown')
                print(f"  📊 Productivity: {productivity.title()}")
                print(f"  🌊 Ecosystem Health: {health.title()}")
            print()
        
        # Reef Proximity
        if hasattr(climate_data, 'reef_proximity') and climate_data.reef_proximity:
            print("🪸 CORAL REEF PROXIMITY")
            print("-" * 40)
            reef_data = climate_data.reef_proximity
            
            nearest_reef = reef_data.get('nearest_reef_distance')
            if nearest_reef is not None:
                print(f"  🏝️ Nearest Reef: {nearest_reef:.1f} km")
            
            reef_zone = reef_data.get('in_reef_zone', False)
            if reef_zone:
                print(f"  🪸 Location: Within coral reef ecosystem")
            else:
                print(f"  🌊 Location: Open ocean environment")
            print()
        
        # Nearby Stations
        if climate_data.nearby_stations:
            print(f"📍 NEARBY WEATHER STATIONS ({len(climate_data.nearby_stations)} found)")
            print("-" * 40)
            for i, station in enumerate(climate_data.nearby_stations[:3], 1):  # Show top 3
                print(f"  {i}. {station.get('name', 'Unknown')} - {station.get('distance_km', 0):.1f} km away")
            print()
        
        # Data Sources and Quality
        print("🔗 DATA SOURCES & QUALITY")
        print("-" * 40)
        for source, confidence in climate_data.data_confidence.items():
            status = "✅" if confidence > 0.7 else "⚠️" if confidence > 0.3 else "❌"
            source_name = source.replace('_', ' ').title()
            print(f"  {status} {source_name}: {confidence:.1%}")
        print()
        
        # File Information
        print("📁 OUTPUT FILES")
        print("-" * 40)
        print(f"  📄 CSV Data: {csv_file.name}")
        print(f"  📊 Parameters Exported: {self._count_csv_parameters(csv_file)}")
        print(f"  💾 File Size: {csv_file.stat().st_size / 1024:.1f} KB")
        print()
        
        print("=" * 80)
    
    def _count_csv_parameters(self, csv_file: Path) -> int:
        """Count the number of parameter rows in the CSV file."""
        try:
            with open(csv_file, 'r') as f:
                lines = f.readlines()
                return len(lines) - 1  # Subtract header row
        except:
            return 0

    def run_enhanced_climate_data(self, coordinates: str, date: str = None, show_report: bool = False) -> List[Path]:
        """Run enhanced coordinate-based climate data collection."""
        
        print("\n🌍 ENHANCED COORDINATE-BASED CLIMATE DATA COLLECTION")
        print("=" * 70)
        print(f"📍 Target coordinates: {coordinates}")
        print(f"📅 Target date: {date or 'Today'}")
        
        # Parse coordinates
        lat, lon = map(float, coordinates.split(','))
        climate_data = self.enhanced_climate_processor.get_comprehensive_climate_data(lat, lon, date)
        
        # Export climate data to CSV
        csv_file = self.enhanced_climate_processor.export_climate_data(climate_data)
        
        # Show detailed report if requested
        if show_report:
            self.print_climate_data_report(climate_data, csv_file)
        
        return [csv_file] if csv_file else []
    
    def run_earth_only(self, force: bool = False) -> Optional[Path]:
        """Generate only NASA Earth base texture."""
        
        print("\n🌍 NASA EARTH BASE TEXTURE GENERATION")
        print("=" * 50)
        
        earth_texture = self.earth_processor.download_earth_base_texture(force=force)
        if earth_texture:
            print("✅ NASA Earth base texture ready")
            
            # Validate Earth texture
            validation = self.validator.validate_texture(str(earth_texture))
            if validation.suitable_for_globe:
                print("✅ Perfect for React Three Fiber globe")
            else:
                print("⚠️ Earth texture may need adjustments")
                
        return earth_texture
    
    def run_sst_only(self, force: bool = False, resolution: str = None) -> Optional[Path]:
        """Generate only ERDDAP SST texture."""
        
        print("\n🌊 ERDDAP SST TEXTURE GENERATION")
        print("=" * 50)
        
        if resolution:
            print(f"📐 Requested resolution: {resolution.upper()}")
        
        print("📡 Downloading pre-rendered SST texture from PacIOOS ERDDAP...")
        sst_texture = self.erddap_sst_processor.download_latest_sst_texture(force=force, resolution=resolution)
        
        if sst_texture:
            print("✅ High-quality ERDDAP SST texture downloaded")
            print("🌊 Source: NOAA Coral Reef Watch (scientific-grade)")
            
            # Validate SST texture
            validation = self.validator.validate_texture(str(sst_texture))
            if validation.suitable_for_globe:
                print("✅ SST texture is React Three Fiber ready")
                
        return sst_texture
    
    def validate_outputs(self) -> bool:
        """Validate existing output files."""
        
        print("\n🔍 VALIDATING EXISTING OUTPUTS")
        print("=" * 40)
        
        validation_passed = True
        
        # Check Earth textures
        earth_dir = config.PATHS['earth_textures_dir']
        earth_files = list(earth_dir.glob("*.jpg")) + list(earth_dir.glob("*.png"))
        
        if earth_files:
            print(f"🌍 Found {len(earth_files)} Earth texture(s)")
            for earth_file in earth_files:
                validation = self.validator.validate_texture(str(earth_file))
                if validation.suitable_for_globe:
                    print(f"✅ {earth_file.name}: Valid")
                else:
                    print(f"❌ {earth_file.name}: Invalid")
                    validation_passed = False
        else:
            print("⚠️ No Earth textures found")
        
        # Check SST textures
        sst_dir = config.PATHS['sst_textures_dir']
        sst_files = list(sst_dir.glob("*.png"))
        
        if sst_files:
            print(f"🌊 Found {len(sst_files)} SST texture(s)")
            for sst_file in sst_files:
                validation = self.validator.validate_texture(str(sst_file))
                if validation.suitable_for_globe:
                    print(f"✅ {sst_file.name}: Valid")
                else:
                    print(f"❌ {sst_file.name}: Invalid")
                    validation_passed = False
        else:
            print("⚠️ No SST textures found")
        
        return validation_passed
    
    def cleanup(self):
        """Clean up resources."""
        try:
            self.earth_processor.close()
            self.erddap_sst_processor.close()
            self.enhanced_climate_processor.close()
            print("✅ System cleanup complete")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

def create_argument_parser():
    """Create and configure argument parser."""
    
    parser = argparse.ArgumentParser(
        description="NOAA Climate Data Globe Texture System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                           # Enhanced climate data (default, medium resolution)
  python main.py --generate                # Random location + detailed report
  python main.py --quick                   # Quick mode: textures only (fast)
  python main.py --resolution=low          # Use low resolution SST (~800KB vs ~11MB)
  python main.py --sst-only --resolution=preview  # Tiny SST texture (~200KB)
  python main.py --earth-only              # NASA Earth texture only
  python main.py --force                   # Force re-download existing files
  python main.py --validate                # Validate existing files
        """
    )
    
    parser.add_argument(
        '--earth-only',
        action='store_true',
        help='Generate only NASA Earth base texture'
    )
    
    parser.add_argument(
        '--sst-only',
        action='store_true',
        help='Generate only ERDDAP SST texture'
    )
    
    parser.add_argument(
        '--coordinates',
        type=str,
        help='Coordinates for climate data (lat,lon format: "40.7128,-74.0060")'
    )
    
    parser.add_argument(
        '--date',
        type=str,
        help='Target date (YYYY-MM-DD format)'
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate existing output files'
    )
    
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick mode: skip climate data collection, only textures'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-download of existing files'
    )
    
    parser.add_argument(
        '--generate',
        action='store_true',
        help='Generate random coordinates and date for data collection with detailed report'
    )
    
    parser.add_argument(
        '--resolution',
        type=str,
        choices=['high', 'medium', 'low', 'preview'],
        default='medium',
        help='SST texture resolution: high (~11MB), medium (~3MB, default), low (~800KB), preview (~200KB)'
    )
    
    parser.add_argument(
        '--websocket-server',
        action='store_true',
        help='Start WebSocket server for real-time Globe integration'
    )
    
    return parser

def main():
    """Main entry point."""
    
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Initialize system
    system = NOAATextureSystem()
    
    try:
        # Handle WebSocket server mode
        if args.websocket_server:
            print("\n🌐 STARTING WEBSOCKET SERVER MODE")
            print("=" * 50)
            print("🚀 Launching real-time server for Globe integration")
            print("📡 Server will be available at ws://localhost:8765")
            print("🌍 Connect your React Three Fiber Globe to start exploring!")
            print("=" * 50)
            
            # Import and start WebSocket server
            try:
                from server.websocket_server import main as websocket_main
                import asyncio
                asyncio.run(websocket_main())
            except ImportError as e:
                print(f"❌ Failed to import WebSocket server: {e}")
                print("Make sure websockets library is installed: pip install websockets")
                sys.exit(1)
            except KeyboardInterrupt:
                print("\n🛑 WebSocket server stopped by user")
                sys.exit(0)
            return
        
        success = False
        result = []
        
        if args.earth_only:
            result = system.run_earth_only(force=args.force)
            success = result is not None
            
        elif args.sst_only:
            result = system.run_sst_only(force=args.force, resolution=args.resolution)
            success = result is not None
            
        elif args.validate:
            success = system.validate_outputs()
            
        else:
            # Enhanced climate data collection (DEFAULT) or Quick mode
            if args.quick:
                print("\n⚡ QUICK MODE: TEXTURES ONLY")
                print("=" * 40)
                print("🚀 Skipping climate data collection for faster execution")
                result = []
            else:
                print("\n🌍 NOAA ENHANCED CLIMATE DATA SYSTEM (DEFAULT)")
                print("=" * 70)
                print("🎯 Using coordinate-based data collection with guaranteed availability")
                print("💡 For quick texture-only mode, use --quick")
                print()
                
                # Generate random coordinates and date if --generate flag is used
                if args.generate:
                    coordinates, date = system.generate_random_location_and_date()
                    print(f"🎲 Generated random location: {coordinates}")
                    print(f"🎲 Generated random date: {date}")
                    result = system.run_enhanced_climate_data(coordinates, date, show_report=True)
                else:
                    # Use provided coordinates or default to NYC
                    coordinates = args.coordinates or "40.7128,-74.0060"
                    result = system.run_enhanced_climate_data(coordinates, args.date)
            
            # Always get SST texture with specified resolution
            print(f"\n🌊 Downloading SST texture (resolution: {args.resolution.upper()})...")
            sst_texture = system.run_sst_only(force=args.force, resolution=args.resolution)
            if sst_texture:
                result.append(sst_texture)
                print("✅ ERDDAP SST texture added to results")
            
            # Always get Earth texture
            print("\n🌍 Ensuring Earth base texture...")
            earth_texture = system.run_earth_only(force=args.force)
            if earth_texture:
                result.append(earth_texture)
                print("✅ NASA Earth texture added to results")
            
            success = len(result) > 0
        
        # Cleanup
        system.cleanup()
        
        # Exit with appropriate code
        if success:
            print("\n🎉 NOAA Climate Data System completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ NOAA Climate Data System completed with errors")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
        system.cleanup()
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        system.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()