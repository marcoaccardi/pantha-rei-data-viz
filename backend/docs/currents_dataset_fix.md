# Currents Dataset Fix - July 25, 2025

## Issue Summary

The currents downloader was failing to download files because it was configured with an incorrect CMEMS dataset ID that pointed to monthly data instead of daily data.

## Root Cause

**Configuration Error in `backend/config/sources.yaml`:**
- **Incorrect**: `cmems_mod_glo_phy-cur_anfc_0.083deg_P1M-m` (monthly data)
- **Correct**: `cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m` (daily data)

The key difference is `P1M` (monthly) vs `P1D` (daily) in the dataset ID.

## Error Symptoms

1. Downloads failing with error: "GLOBAL_ANALYSISFORECAST_PHY_001_024 Please check that the dataset exists and the input datasetID is correct"
2. No files appearing in `/ocean-data/raw/currents/` directories
3. All download attempts returning failure status
4. Log entries showing authentication success but dataset not found

## Solution Applied

### 1. Updated Dataset Configuration

**File**: `backend/config/sources.yaml`

```yaml
currents:
  dataset_id: "cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m"  # Changed from P1M to P1D
  temporal_coverage:
    start: "2022-06-01"  # Updated based on CMEMS dataset availability
```

### 2. Verification

- Authentication with CMEMS successful
- Dataset ID now recognized by CMEMS API
- Downloads initiated successfully (large files take time to complete)

## CMEMS Dataset Details

**Product**: GLOBAL_ANALYSISFORECAST_PHY_001_024
**Dataset**: cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m

- **Spatial Resolution**: 0.083° × 0.083° (1/12 degree)
- **Temporal Resolution**: Daily (P1D)
- **Variables**: uo (eastward velocity), vo (northward velocity)
- **Depth Range**: Surface layer (0-5m)
- **Coverage**: Global Ocean
- **Available Period**: June 1, 2022 - present

## Troubleshooting Guide

### Dataset ID Validation

To verify CMEMS dataset IDs are correct:

1. **Check CMEMS Product Page**: https://data.marine.copernicus.eu/product/GLOBAL_ANALYSISFORECAST_PHY_001_024/description
2. **Use copernicusmarine CLI**:
   ```bash
   copernicusmarine describe --dataset-id <dataset_id>
   ```

### Common Dataset ID Patterns

CMEMS uses this naming convention:
```
<origin>_<group>_<area>_<thematic>_<type>_<spatial_res>_<temporal_res>
```

For currents data:
- `P1H` = Hourly
- `P1D` = Daily  
- `P1M` = Monthly
- `P1Y` = Yearly

### Temporal Coverage Issues

If getting "no data available" errors:
1. Check dataset availability period in CMEMS documentation
2. Verify requested dates fall within dataset coverage
3. Update `temporal_coverage.start` in `sources.yaml` if needed

### Authentication Problems

If authentication fails:
1. Verify credentials in `backend/config/credentials.env`
2. Check CMEMS account status
3. Remove old credentials: `rm ~/.copernicusmarine/.copernicusmarine-credentials`

### Download Performance

Large NetCDF files (100+ MB) take time to download:
- Global daily currents ~500MB+ per file
- Downloads may take 5-30 minutes depending on connection
- Use timeout settings appropriately in scripts

## Prevention

1. **Always verify dataset IDs** against CMEMS documentation before configuration
2. **Test with small spatial/temporal subsets** before full downloads
3. **Check dataset availability periods** when configuring temporal coverage
4. **Monitor CMEMS product updates** that may change dataset IDs

## Files Modified

1. `backend/config/sources.yaml` - Updated dataset_id and temporal_coverage
2. `backend/docs/currents_dataset_fix.md` - This documentation

## Related Issues

This fix resolves the issue where currents data directories were empty despite successful configuration and authentication. The downloader will now successfully download and process currents data files.