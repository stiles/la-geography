# LA geography

A dependable and clean repository of Los Angeles administrative and physical boundary layers for reproducible analysis and easy mapping. 

## Purpose

Provides clean, versioned, well-documented boundary layers for LA city & County with:
- **Official sources** from open data portals maintained by LA city and LA County
- **Standardized outputs** in WGS84 (EPSG:4326)
- **Area calculations** using California Albers (EPSG:3310) for accuracy
- **Normalized schemas** with consistent lower_snake_case naming
- **Quality validation** with geometry checks and expected feature counts

## Available Layers

### LAPD (police)
- **Bureaus** (4): Central, South, Valley, West
- **Divisions** (21): Pacific, Rampart, Central, etc.
- **Reporting Districts** (~1,191): Finest-grained LAPD geography
- **Station Locations** (21): Police station addresses and locations

### LA city
- **City Boundary**: Official city limits
- **Neighborhoods**: LA Times boundaries (officially adopted)
- **Neighborhood Councils**: ~99 certified councils
- **Council Districts**: 15 city council districts
- **Parks**: 561 parks and recreation facilities

### LA County
- **County boundary**: LA County limits
- **Cities & communities**: 88 cities + unincorporated areas
- **School Districts**: 85 school districts (Elementary, High School, and Unified)

### Fire Departments
- **LA County Fire - Station Boundaries** (174): LA County Fire station service areas
- **LA County Fire - Station Locations** (174): LA County Fire station addresses  
- **LA Fire Dept - Station Boundaries** (102): LAFD (city) station service areas

### Transportation
- **Freeways**: Interstates and state highways clipped to LA County
- **Metro Lines**: LA Metro rail lines and bus rapid transit (17 lines)

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

**Direct Download URLs:**

All layers are publicly accessible via HTTPS. Use these URLs directly in your GIS tools, notebooks, or scripts:

| Layer | URL | Size |
|-------|-----|------|
| **LAPD bureaus** | https://stilesdata.com/la-geography/lapd_bureaus.geojson | 0.55 MB |
| **LAPD divisions** | https://stilesdata.com/la-geography/lapd_divisions.geojson | 0.84 MB |
| **LAPD reporting districts** | https://stilesdata.com/la-geography/lapd_reporting_districts.geojson | 6.50 MB |
| **LAPD station locations** | https://stilesdata.com/la-geography/lapd_station_locations.geojson | 0.01 MB |
| **LA city boundary** | https://stilesdata.com/la-geography/la_city_boundary.geojson | 0.40 MB |
| **LA city neighborhoods** | https://stilesdata.com/la-geography/la_city_neighborhoods.geojson | 0.95 MB |
| **LA city neighborhood councils** | https://stilesdata.com/la-geography/la_city_neighborhood_councils.geojson | 2.80 MB |
| **LA city council districts** | https://stilesdata.com/la-geography/la_city_council_districts.geojson | 1.40 MB |
| **LA city parks** | https://stilesdata.com/la-geography/la_city_parks.geojson | 5.00 MB |
| **LA County boundary** | https://stilesdata.com/la-geography/la_county_boundary.geojson | 2.80 MB |
| **LA County cities** | https://stilesdata.com/la-geography/la_county_cities.geojson | 13.53 MB |
| **LA County school districts** | https://stilesdata.com/la-geography/la_county_school_districts.geojson | 4.30 MB |
| **LA freeways (interstates and state highways)** | https://stilesdata.com/la-geography/la_freeways.geojson | 1.62 MB |
| **LA Metro lines** | https://stilesdata.com/la-geography/la_metro_lines.geojson | 0.44 MB |
| **LA County Fire Dept station boundaries** | https://stilesdata.com/la-geography/lacofd_station_boundaries.geojson | 5.10 MB |
| **LA County Fire Dept station locations** | https://stilesdata.com/la-geography/lacofd_station_locations.geojson | 0.10 MB |
| **LA Fire Dept (city) station boundaries** | https://stilesdata.com/la-geography/lafd_station_boundaries.geojson | 1.70 MB |
| **Metadata** | https://stilesdata.com/la-geography/metadata.json | JSON |

**Quick examples:**
```python
# Python with GeoPandas
import geopandas as gpd
la_city = gpd.read_file('https://stilesdata.com/la-geography/la_city_boundary.geojson')

# R with sf
library(sf)
la_city <- st_read('https://stilesdata.com/la-geography/la_city_boundary.geojson')
```

```javascript
// JavaScript with D3
d3.json('https://stilesdata.com/la-geography/la_city_boundary.geojson')
  .then(data => {
    const projection = d3.geoMercator().fitSize([width, height], data);
    const path = d3.geoPath().projection(projection);
    svg.selectAll('path').data(data.features)
       .enter().append('path').attr('d', path);
  });
```

**Environment Setup:**
To upload layers, set these environment variables:
```bash
export MY_AWS_ACCESS_KEY_ID="your-key"
export MY_AWS_SECRET_ACCESS_KEY="your-secret"
export MY_PERSONAL_PROFILE="personal"  # For clarity (optional)
```

## Directory structure

```
la-geography/
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

## Output format

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

- **LA city geo hub**: https://geohub.lacity.org/
- **LA County GIS hub**: https://egis-lacounty.hub.arcgis.com/
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