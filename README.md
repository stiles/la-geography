# la-geo

A dependable repository of Los Angeles administrative and physical boundary layers for reproducible analysis and mapping.

## Purpose

Provides clean, versioned, well-documented boundary layers for LA City & County with:
- **Official sources** from LA City GeoHub and LA County GIS Hub
- **Standardized outputs** in WGS84 (EPSG:4326)
- **Area calculations** using California Albers (EPSG:3310) for accuracy
- **Normalized schemas** with consistent lower_snake_case naming
- **Quality validation** with geometry checks and expected feature counts

## Available Layers

### LAPD Geographies
- **Bureaus** (4): Central, South, Valley, West
- **Divisions** (21): Central, Rampart, Southwest, etc.
- **Reporting Districts** (~1,191): Finest-grained LAPD geography

### LA City
- **City Boundary**: Official city limits
- **Neighborhoods**: LA Times boundaries (officially adopted)
- **Neighborhood Councils**: ~99 certified councils

### LA County
- **County Boundary**: LA County limits
- **Cities & Communities**: 88 cities + unincorporated areas

### Transportation
- **Freeways**: National Highway System clipped to LA County

## Quick Start

```bash
# Set up environment
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt

# Fetch all layers
make fetch

# Process and validate
make standardize validate

# Export final outputs
make export
```

## S3 Storage

Processed layers are published to S3 for public access:

```bash
# Upload all layers to S3
make s3-upload

# Download layers from S3 (if you just need the data)
make s3-download

# List available layers in S3
make s3-list

# Upload a single layer
python scripts/s3_sync.py upload --layer la_city_boundary
```

**Public URLs:**
- Base: `https://stilesdata.com/la-geography/`
- Example: `https://stilesdata.com/la-geography/la_city_boundary.geojson`
- Metadata: `https://stilesdata.com/la-geography/metadata.json`

**Environment Setup:**
To upload layers, set these environment variables:
```bash
export MY_AWS_ACCESS_KEY_ID="your-key"
export MY_AWS_SECRET_ACCESS_KEY="your-secret"
export MY_PERSONAL_PROFILE="personal"  # For clarity (optional)
```

## Directory Structure

```
la-geo/
├── README.md              # This file
├── PLANNING.md            # Detailed planning document
├── config/
│   └── layers.yml         # Layer endpoints and configurations
├── data/
│   ├── raw/               # Immutable source data
│   ├── standard/          # Cleaned and normalized outputs
│   └── docs/              # Sample maps and quicklooks
├── scripts/
│   ├── fetch_boundaries.py  # Fetch layers from sources
│   ├── process_raw.py        # Process complex layers
│   ├── geo_utils.py          # Shared utilities
│   └── s3_sync.py            # Upload/download from S3
└── tests/
    └── test_validate.py
```

## Output Format

All layers in `data/standard/` include:

- **Geometry**: EPSG:4326 (WGS84)
- **Format**: GeoJSON and Parquet
- **Fields**:
  - `geometry`: Feature geometry
  - `area_sqmi`: Area in square miles (polygons only, calculated in EPSG:3310)
  - `source_url`: Origin REST endpoint
  - `fetched_at`: ISO timestamp
  - Normalized field names in lower_snake_case

## Configuration

Layer endpoints are defined in `config/layers.yml` with:
- Source URL
- Expected feature count (for validation)
- Field mappings for normalization
- Geometry type
- Source organization

## Data Sources

- **LA City GeoHub**: https://geohub.lacity.org/
- **LA County GIS Hub**: https://egis-lacounty.hub.arcgis.com/
- **Caltrans**: https://caltrans-gis.dot.ca.gov/

All sources are official government portals with open data licenses.

## Coordinate Reference Systems

- **Storage & sharing**: EPSG:4326 (WGS84 lat/lon)
- **Area/distance calculations**: EPSG:3310 (California Albers, equal-area)

This avoids Web Mercator distortion while maintaining compatibility with web mapping tools.

## Validation

Each fetch includes automated checks:
- Non-empty features, no null geometries
- Valid geometries (auto-fixed with `buffer(0)`)
- Feature counts within expected tolerance
- Bounding box inside LA County extent
- LAPD hierarchy validation (districts ≥ divisions ≥ bureaus)

## License

Data sources retain their original licenses (typically public domain or CC0). See `data/standard/*.meta.json` for per-layer licensing information.

## Development

- Python 3.10+
- Key dependencies: geopandas, shapely, pyproj, pyarrow, ezesri
- Managed with `uv` for reproducible environments

## Roadmap

- **Phase 1** (Current): Core boundaries with official sources ✅
- **Phase 2**: Census block apportionment for demographics
- **Phase 3**: Documentation site with data dictionary
- **Phase 4**: Scheduled refreshes with change logs

## Contact

See [PLANNING.md](PLANNING.md) for detailed methodology and design decisions.

