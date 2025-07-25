# Waves Dataset Monitoring & Transition Plan

## Current Configuration

### Dataset Information
- **Product ID**: `GLOBAL_ANALYSISFORECAST_WAV_001_027`
- **Source**: CMEMS (Copernicus Marine Environment Monitoring Service)
- **Institution**: Météo-France
- **Expiry Date**: **August 4, 2025** ⚠️
- **Spatial Resolution**: 0.083° (~9km at equator)
- **Temporal Resolution**: Hourly, with daily analyses and 10-day forecasts
- **Coverage**: Global Ocean (80°S to 80°N)

### Variables Available
1. **VHM0** - Significant Wave Height
   - Units: meters (m)
   - Range: 0.1 - 15.0m (typical)
   - Description: Spectral significant wave height (Hm0)

2. **MWD** - Mean Wave Direction  
   - Units: degrees (°)
   - Range: 0 - 360°
   - Description: Mean wave direction from (nautical convention)

3. **PP1D** - Peak Wave Period
   - Units: seconds (s)
   - Range: 3.0 - 20.0s (typical)
   - Description: Peak wave period at variance spectral density maximum

## Monitoring System

### Automated Checks
The monitoring system provides:
- **Daily validity checks** when WavesDownloader is initialized
- **Status alerts** at 90, 60, and 30 days before expiration
- **Critical warnings** when dataset is expired or expires within 30 days
- **JSON and human-readable reports** via monitoring script

### Monitoring Script Usage
```bash
# Check all datasets
python scripts/monitor_dataset_validity.py

# JSON output for automation
python scripts/monitor_dataset_validity.py --json

# Check specific dataset
python scripts/monitor_dataset_validity.py --dataset waves
```

### Status Levels
- **Healthy**: > 90 days until expiry
- **Warning**: 30-90 days until expiry
- **Critical**: < 30 days until expiry  
- **Expired**: Past expiry date

## Alternative Datasets

### Primary Alternative
- **Product ID**: `GLOBAL_MULTIYEAR_WAV_001_032`
- **Type**: Reanalysis (historical data)
- **Expiry**: May 31, 2025
- **Note**: Also expiring soon, not a long-term solution

### Future Options
- Monitor CMEMS roadmap for successor products
- Regional datasets with higher resolution (limited coverage)
- Satellite-based wave products (different data structure)

## Transition Strategy

### Phase 1: Immediate (January - March 2025)
1. **Monitor CMEMS announcements** for replacement dataset
2. **Subscribe to notifications** at CMEMS user portal
3. **Test alternative datasets** if available
4. **Document compatibility requirements**

### Phase 2: Preparation (April - July 2025)
1. **Implement configuration switching** mechanism
2. **Test new dataset** when announced
3. **Update API compatibility** if needed
4. **Prepare deployment** for seamless transition

### Phase 3: Transition (August 2025)
1. **Deploy new configuration** before August 4, 2025
2. **Monitor service continuity**
3. **Update documentation** and API responses
4. **Verify data quality** and consistency

## API Impact Assessment

### Current API Response Structure
```json
{
  "location": "Sample Location",
  "coordinates": {"lat": 40.7, "lon": -74.0},
  "timestamp": "2024-01-15T00:00:00Z",
  "wave_data": {
    "significant_height_m": 1.85,
    "mean_direction_deg": 304.0,
    "peak_period_s": 8.7
  },
  "metadata": {
    "data_source": "CMEMS GLOBAL_ANALYSISFORECAST_WAV_001_027",
    "institution": "Météo-France",
    "spatial_resolution": "0.083°",
    "temporal_resolution": "hourly"
  }
}
```

### Potential Changes Required
- **Dataset ID** in metadata will change
- **Institution** may change (unlikely)
- **Variable names** should remain consistent (VHM0, MWD, PP1D)
- **Spatial/temporal resolution** may change
- **Coverage dates** will extend beyond August 2025

## Risk Mitigation

### High Priority Actions
1. **Set up automated monitoring** (✅ Complete)
2. **Subscribe to CMEMS notifications**
3. **Identify backup data sources**
4. **Plan API versioning** for smooth transitions

### Contingency Plans
1. **Service interruption**: Use cached data with timestamps
2. **Data format changes**: Implement adapter patterns
3. **Coverage gaps**: Use regional datasets for critical areas
4. **Complete failure**: Switch to satellite-based alternatives

## Contact Information

### CMEMS Support
- **Website**: https://marine.copernicus.eu
- **Roadmap**: https://marine.copernicus.eu/user-corner/product-roadmap
- **Support**: https://help.marine.copernicus.eu

### Internal Monitoring
- **Script**: `backend/scripts/monitor_dataset_validity.py`
- **Configuration**: `backend/config/sources.yaml`
- **Implementation**: `backend/downloaders/waves_downloader.py`

## Timeline Checkpoints

| Date | Action | Status |
|------|--------|--------|
| January 2025 | Set up monitoring system | ✅ Complete |
| March 2025 | Review alternatives if no successor announced | Pending |
| May 2025 | Implement emergency fallback if needed | Pending |
| July 2025 | Execute transition to new dataset | Pending |
| August 4, 2025 | **Dataset expires** | ⚠️ Critical |

---

**Last Updated**: July 25, 2025  
**Next Review**: March 1, 2025  
**Monitoring Status**: 🚨 Critical - 9 days until expiry