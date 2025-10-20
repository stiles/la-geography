# Project Status

_Last updated: 2025-10-19_

## ✅ Completed

### Phase 0: Repository Bootstrap

- [x] Project structure created (`data/`, `scripts/`, `config/`, `tests/`)
- [x] Configuration system (`config/layers.yml`)
- [x] Core utilities module (`scripts/geo_utils.py`)
- [x] Updated fetch script (`scripts/fetch_boundaries.py`)
- [x] Makefile with pipeline targets
- [x] README and documentation
- [x] Requirements file with dependencies
- [x] `.gitignore` configured

### Documentation

- [x] `PLANNING.md` - Detailed methodology and design
- [x] `README.md` - User-facing documentation
- [x] `AVAILABLE_LAYERS.md` - Survey of official data sources
- [x] `STATUS.md` - This file

### Configuration

All layers configured in `config/layers.yml` with official REST endpoints:

✅ **LAPD Boundaries**
- `lapd_bureaus` - 4 bureaus
- `lapd_divisions` - 21 divisions  
- `lapd_reporting_districts` - ~1,191 districts

✅ **LA City**
- `la_city_boundary` - Official city limits
- `la_city_neighborhood_councils` - ~99 councils
- ⚠️ `la_city_neighborhoods` - LA Times boundaries (endpoint TBD)

✅ **LA County**
- `la_county_boundary` - County limits
- `la_county_cities` - 88 cities + unincorporated areas

✅ **Transportation**
- `la_freeways` - National Highway System (will clip to LA County)

### Core Utilities (`scripts/geo_utils.py`)

- [x] `area_sqmi()` - Calculate area using EPSG:3310 (California Albers)
- [x] `ensure_wgs84()` - CRS standardization
- [x] `normalize_columns()` - Field name normalization
- [x] `add_area_if_polygon()` - Automatic area calculation
- [x] `add_metadata()` - Source URL and timestamp
- [x] `validate_bbox()` - LA County extent check
- [x] `fix_geometries()` - Auto-fix invalid geometries
- [x] `clip_to_boundary()` - Spatial clipping (for freeways)

## 🚧 In Progress

### Fetch Script Enhancement

Current `scripts/fetch_boundaries.py` features:
- Configuration-driven from `layers.yml`
- Uses `geo_utils` helper functions
- Area calculated in EPSG:3310 (not Web Mercator)
- Automatic validation checks
- LAPD hierarchy validation

Still needed:
- [ ] Handle layer filters (e.g., `TYPE = 'LA County'` for county boundary)
- [ ] Implement clipping for freeways layer
- [ ] Create metadata sidecar files (`.meta.json`)

## 📋 Next Steps

### Immediate (Phase 1)

1. **Find LA Times Neighborhoods endpoint**
   - Check GeoHub item page for FeatureServer URL
   - Update `config/layers.yml` once found

2. **Test fetch script**
   ```bash
   # Create virtual environment
   uv venv && source .venv/bin/activate
   uv pip install -r requirements.txt
   
   # Test with single layer
   python scripts/fetch_boundaries.py --out data/raw/ --layers lapd_bureaus
   
   # Fetch all layers
   make fetch
   ```

3. **Create remaining pipeline scripts**
   - `scripts/standardize.py` - Field mapping and normalization
   - `scripts/validate.py` - Comprehensive validation checks
   - `scripts/export.py` - Export to Parquet + metadata files
   - `scripts/quicklook.py` - Generate preview maps

4. **Implement special handling**
   - Filter layer (county boundary: `TYPE = 'LA County'`)
   - Clip layer (freeways to LA County boundary)
   - Field mapping for different source schemas

### Short-term (Phase 1)

5. **Testing**
   - Create `tests/test_validate.py`
   - Test area calculations
   - Test bbox validation
   - Test LAPD hierarchy

6. **Metadata**
   - Generate `.meta.json` files for each layer
   - Include source URL, license, fetch date, field descriptions
   - Document expected counts and update frequencies

7. **Documentation**
   - Field dictionaries for each layer
   - Usage examples
   - Update frequency notes

### Medium-term (Phase 2)

8. **Census Integration**
   - Fetch 2020 Census blocks
   - Implement area-weighted apportionment
   - Attach demographics to target geographies

9. **Automation**
   - Scheduled refreshes
   - Change detection and logging
   - Automated validation reports

### Long-term (Phase 3-4)

10. **Documentation Site**
    - Interactive layer gallery
    - Data dictionary
    - Sample maps

11. **S3 Integration**
    - Upload/download from S3
    - Versioned snapshots
    - Public access URLs

## Known Issues

1. **LA Times Neighborhoods** - REST endpoint not yet identified
   - Hub page: https://geohub.lacity.org/datasets/lahub::la-times-neighborhood-boundaries/about
   - Need to find FeatureServer URL from item metadata

2. **Existing fetch scripts** - Old scripts in repo use S3 sources and Web Mercator
   - `fetch_boundaries.py` - Now updated ✅
   - `fetch_lapd_boundaries.py` - Can be deprecated (functionality merged)

## Testing Checklist

Before declaring Phase 1 complete:

- [ ] All layers fetch successfully
- [ ] Area calculations match expected values (spot check)
- [ ] LAPD hierarchy validates correctly
- [ ] All outputs in WGS84 (EPSG:4326)
- [ ] Area calculated in EPSG:3310 (California Albers)
- [ ] Field names normalized (lower_snake_case)
- [ ] Metadata fields present (`source_url`, `fetched_at`, `area_sqmi`)
- [ ] Geometries valid (no topology errors)
- [ ] Feature counts within expected tolerance
- [ ] Bounding boxes within LA County extent

## Commands

```bash
# Setup
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt

# Fetch all layers
make fetch

# Fetch specific layers
python scripts/fetch_boundaries.py --out data/raw/ --layers lapd_bureaus la_city_boundary

# Full pipeline (when implemented)
make all
```

## Project Health

- **Configuration**: ✅ Complete
- **Utilities**: ✅ Complete
- **Fetch**: ✅ Core complete, enhancements needed
- **Standardize**: ⚠️ Not yet implemented
- **Validate**: ⚠️ Not yet implemented
- **Export**: ⚠️ Not yet implemented
- **Testing**: ❌ Not yet implemented
- **Documentation**: ✅ Good coverage

