import netCDF4
import numpy as np
import datetime
import sys
from pathlib import Path

# Add project root to path and import config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from config import PATHS
except ImportError:
    # Fallback configuration if config import fails
    BASE_DIR = Path(__file__).parent.parent.parent
    PATHS = {
        'currents_data_dir': BASE_DIR / "data" / "ocean_datasets" / "currents_2021_2023"
    }

def get_current_data(date_str, lat, lon):
    """
    Get ocean current data from NetCDF files using relative paths.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        
    Returns:
        Dictionary with ocean current U and V components
    """
    # Convert the date string to a datetime object
    date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
    
    # Open the NetCDF file using relative path from config
    date_str_file = date_str.replace('-', '')
    data_file = PATHS['currents_data_dir'] / f"oscar_currents_nrt_{date_str_file}.dap.nc4"
    
    # Check if file exists
    if not data_file.exists():
        raise FileNotFoundError(f"Ocean currents data file not found: {data_file}")
    
    print(f"🌊 Loading ocean currents from: {data_file}")

    ocean_current_file = netCDF4.Dataset(str(data_file))

    # Get the index of the desired date in the time dimension
    time_var = ocean_current_file.variables['time']
    time_index = netCDF4.date2index(
        date, time_var, select='nearest', calendar=time_var.calendar)

    # Get the latitude and longitude variables
    lat_var = ocean_current_file.variables['lat'][:]
    lon_var = ocean_current_file.variables['lon'][:]

    # Convert the longitude range from 0-359.75 to -180-180 degrees
    lon_var[lon_var > 180] -= 360

    # Get the index of the nearest latitude and longitude values
    lat_index = np.abs(lat_var - lat).argmin()
    lon_index = np.abs(lon_var - lon).argmin()

    # Get the data for the desired date, latitude, and longitude
    data_u = ocean_current_file.variables['u'][time_index,
                                               lat_index, lon_index]
    data_v = ocean_current_file.variables['v'][time_index,
                                               lat_index, lon_index]

    # Convert MaskedArray objects to regular numpy arrays
    # data_u = np.ma.filled(data_u, np.nan)
    # data_v = np.ma.filled(data_v, np.nan)
    print("data_u", data_u, data_v)

    # Close the NetCDF file
    ocean_current_file.close()

    # Return the data for the desired location
    return {'u': data_u.tolist(), 'v': data_v.tolist()}


# print(get_current_data("2021-01-01", - 41.03, 30.50))
