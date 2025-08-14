# Legacy Individual Updaters

**Maintained for backward compatibility - Use production scripts for new development**

These scripts provide individual dataset update functionality and are kept for specific use cases where the main production pipeline may not be suitable.

## Scripts Overview

### Individual Dataset Updaters
- **`update_sst_data.py`** - Sea Surface Temperature data updates
- **`update_currents_data.py`** - Ocean currents data updates  
- **`update_acidity_data.py`** - Ocean acidity data updates
- **`update_microplastics_data.py`** - Microplastics data updates

### Legacy Comprehensive Script
- **`update_all_data.sh`** - Comprehensive 520-line legacy update script

## Current Status

### ✅ Superseded by Production Scripts
The main production workflow now uses:
- `scripts/production/update_ocean_data.sh` (preferred)
- `scripts/production/update_ocean_data.py` (orchestrator)

### 🔄 Compatibility Maintained
These legacy scripts are maintained for:
- Backward compatibility with existing workflows
- Specific dataset-only operations
- Development and testing scenarios
- Emergency fallback procedures

## Usage Patterns

### Individual Dataset Updates
```bash
# Update only SST data
python scripts/legacy_individual_updaters/update_sst_data.py --yesterday

# Update only currents
python scripts/legacy_individual_updaters/update_currents_data.py --date 2024-01-15

# Update only acidity data
python scripts/legacy_individual_updaters/update_acidity_data.py --recent 7

# Update only microplastics
python scripts/legacy_individual_updaters/update_microplastics_data.py --validate
```

### Legacy Comprehensive Updates
```bash
# Use legacy comprehensive script
./scripts/legacy_individual_updaters/update_all_data.sh -d sst,currents
./scripts/legacy_individual_updaters/update_all_data.sh --datasets acidity --verbose
```

## When to Use Legacy Scripts

### ✅ Appropriate Use Cases
- **Single Dataset Focus**: When you need to update only one specific dataset
- **Development Testing**: Testing individual dataset pipelines
- **Troubleshooting**: Isolating issues to specific data sources
- **Custom Workflows**: Integrating with external systems that expect individual scripts
- **Emergency Recovery**: Fallback when main production scripts have issues

### ❌ Not Recommended For
- **Production Operations**: Use `scripts/production/update_ocean_data.sh` instead
- **Daily Updates**: Production scripts provide better orchestration
- **New Development**: Build on the production pipeline foundation
- **System Integration**: Production scripts have better error handling and logging

## Script Characteristics

### Individual Updaters (53 lines each)
- Lightweight, focused functionality
- Basic error handling
- Direct API interactions
- Minimal logging and validation

### Legacy Comprehensive Script (520 lines)
- Full-featured but complex
- Extensive command-line options
- Comprehensive error handling
- Historical development artifact

## Migration Path

If you're currently using these legacy scripts:

1. **Evaluate**: Determine if production scripts meet your needs
2. **Test**: Try `scripts/production/update_ocean_data.sh` with your use case
3. **Migrate**: Update processes to use production scripts
4. **Validate**: Ensure outputs match expectations
5. **Maintain**: Keep legacy scripts as fallback only

## Maintenance Policy

- **Bug Fixes**: Critical bugs will be fixed
- **Feature Development**: No new features will be added
- **Documentation**: Basic documentation maintained
- **Testing**: Limited testing compared to production scripts
- **Long-term**: Scripts will be deprecated when production scripts fully replace all use cases

These scripts serve as a bridge during the transition to the new production pipeline while ensuring no existing workflows are disrupted.