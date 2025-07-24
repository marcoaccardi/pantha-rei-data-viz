import xarray as xr
import numpy as np
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
        'biological_data_dir': BASE_DIR / "data" / "ocean_datasets" / "biological"
    }

# EXTRACT THE MEAN BETWEEN 12:00 - 00:00

def get_bio_data(date_str, lat, lon):
    """
    Get biological ocean data from NetCDF files using relative paths.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        
    Returns:
        Dictionary with biological ocean data
    """
    # Open the netcdf file using relative path from config
    data_file = PATHS['biological_data_dir'] / f"{date_str}.nc"
    
    # Check if file exists
    if not data_file.exists():
        raise FileNotFoundError(f"Biological data file not found: {data_file}")
    
    print(f"📊 Loading biological data from: {data_file}")

    ds = xr.open_dataset(str(data_file))
    # Find the indices for the nearest latitude and longitude values in the dataset
    lat_idx = abs(ds.latitude - lat).argmin().item()
    lon_idx = abs(ds.longitude - lon).argmin().item()

    # Extract the mean data for each variable for the specified latitude and longitude and both time points
    spco2_mean = ds.spco2[:, lat_idx, lon_idx].mean().item()
    o2_mean = ds.o2[:, :, lat_idx, lon_idx].mean().item()
    chl_mean = ds.chl[:, :, lat_idx, lon_idx].mean().item()
    no3_mean = ds.no3[:, :, lat_idx, lon_idx].mean().item()
    po4_mean = ds.po4[:, :, lat_idx, lon_idx].mean().item()
    phyc_mean = ds.phyc[:, :, lat_idx, lon_idx].mean().item()
    si_mean = ds.si[:, :, lat_idx, lon_idx].mean().item()
    ph_mean = ds.ph[:, :, lat_idx, lon_idx].mean().item()
    talk_mean = ds.talk[:, :, lat_idx, lon_idx].mean().item()
    nppv_mean = ds.nppv[:, :, lat_idx, lon_idx].mean().item()
    dissic_mean = ds.dissic[:, :, lat_idx, lon_idx].mean().item()
    fe_mean = ds.fe[:, :, lat_idx, lon_idx].mean().item()

    # Print the mean values for each variable
    # print(f"spco2_mean: {spco2_mean}")
    # print(f"o2_mean: {o2_mean}")
    # print(f"chl_mean: {chl_mean}")
    # print(f"no3_mean: {no3_mean}")
    # print(f"po4_mean: {po4_mean}")
    # print(f"phyc_mean: {phyc_mean}")
    # print(f"si_mean: {si_mean}")
    # print(f"ph_mean: {ph_mean}")
    # print(f"talk_mean: {talk_mean}")
    # print(f"nppv_mean: {nppv_mean}")
    # print(f"dissic_mean: {dissic_mean}")
    # print(f"fe_mean: {fe_mean}")

    # Close the netcdf file
    ds.close()
    data_result = {
        "spco2_mean": spco2_mean,
        "o2_mean": o2_mean,
        "chl_mean": chl_mean,
        "no3_mean": no3_mean,
        "po4_mean": po4_mean,
        "phyc_mean": phyc_mean,
        "si_mean": si_mean,
        "ph_mean": ph_mean,
        "talk_mean": talk_mean,
        "nppv_mean": nppv_mean,
        "dissic_mean": dissic_mean,
        "fe_mean": fe_mean
    }
    # print(data_result)
    return data_result


# get_bio_data("2021-01-01", - 41.03, 30.50)
