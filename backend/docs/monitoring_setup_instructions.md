# Dataset Monitoring Setup Instructions

## Overview
This guide covers setting up automated monitoring for CMEMS dataset validity, ensuring continuity of ocean data services.

## Quick Setup

### 1. Install Monitoring System
```bash
# Navigate to backend directory
cd backend  # Navigate to your project's backend directory

# Ensure virtual environment is active
source .venv/bin/activate

# Test monitoring script
python scripts/monitor_dataset_validity.py
```

### 2. Set Up Automated Alerts (Optional)
```bash
# Run the alert setup script
./scripts/setup_monitoring_alerts.sh
```

This will configure:
- **Daily checks** at 9 AM
- **Weekly reports** on Mondays at 8 AM  
- **Critical alerts** every 6 hours when datasets are expiring

## Manual Monitoring

### Check Dataset Status
```bash
# Human-readable report
python scripts/monitor_dataset_validity.py

# JSON output for automation
python scripts/monitor_dataset_validity.py --json

# Check specific dataset
python scripts/monitor_dataset_validity.py --dataset waves
```

### Current Status (as of July 25, 2025)
```
🚨 CRITICAL: GLOBAL_ANALYSISFORECAST_WAV_001_027 expires in 9 days!
📅 Expiry Date: August 4, 2025
🎯 Action Required: Find replacement dataset immediately
```

## Integration with Code

### Automatic Checks
The monitoring is integrated into the WavesDownloader class:
```python
from downloaders.waves_downloader import WavesDownloader

# Monitoring happens automatically on initialization
downloader = WavesDownloader()

# Get current status programmatically
status = downloader.get_dataset_status()
print(f"Days until expiry: {status['days_until_expiry']}")
```

### API Health Checks
You can integrate dataset status into API health endpoints:
```python
# In your FastAPI application
@app.get("/health/datasets")
async def dataset_health():
    from downloaders.waves_downloader import WavesDownloader
    
    try:
        downloader = WavesDownloader()
        status = downloader.get_dataset_status()
        return {"waves": status}
    except Exception as e:
        return {"waves": {"status": "error", "error": str(e)}}
```

## Monitoring Outputs

### Status Levels
- **🟢 Healthy**: > 90 days until expiry
- **🟡 Warning**: 30-90 days until expiry  
- **🔴 Critical**: < 30 days until expiry
- **💀 Expired**: Past expiry date

### Log Locations
- **Monitoring logs**: `/ocean-data/logs/dataset_monitoring.log`
- **Download logs**: `/ocean-data/logs/waves_downloader.log`
- **System logs**: Check via monitoring script output

## Troubleshooting

### Common Issues

**1. "Module not found" errors**
```bash
# Ensure all dependencies are installed
source .venv/bin/activate
uv pip install -r requirements.txt
```

**2. Cron jobs not working**
```bash
# Check cron service is running
sudo launchctl list | grep cron

# View cron logs on macOS
log show --predicate 'subsystem == "com.apple.cron"' --last 1h
```

**3. Permission errors**
```bash
# Make scripts executable
chmod +x scripts/*.sh
chmod +x scripts/*.py
```

### Testing Cron Jobs Manually
```bash
# Test the exact command that cron would run
cd backend  # Navigate to your project's backend directory
.venv/bin/python scripts/monitor_dataset_validity.py >> ../ocean-data/logs/dataset_monitoring.log 2>&1
```

## Next Steps

### Immediate Actions (Before August 4, 2025)
1. **Monitor CMEMS roadmap** daily for replacement announcements
2. **Subscribe to CMEMS notifications** 
3. **Identify backup data sources**
4. **Test alternative datasets** if available

### Long-term Strategy
1. **Implement configuration switching** for seamless transitions
2. **Add support for multiple datasets** as fallbacks
3. **Create API versioning** to handle data source changes
4. **Document transition procedures** for future dataset changes

## Resources

### CMEMS Links
- **Product Roadmap**: https://marine.copernicus.eu/user-corner/product-roadmap
- **User Notifications**: https://marine.copernicus.eu/user-corner/user-notification-service
- **Support**: https://help.marine.copernicus.eu

### Internal Documentation
- **Dataset Analysis**: `docs/waves_dataset_monitoring.md`
- **API Structure**: `/ocean-data/waves/api_structure_analysis.json`
- **Implementation**: `docs/waves_implementation_summary.md`

---

**⚠️ URGENT**: Current dataset expires August 4, 2025 (9 days)  
**📋 Status**: Monitoring system active and alerting  
**🎯 Priority**: Find replacement dataset immediately