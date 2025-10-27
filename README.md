# LA geography

A dependable and clean repository of Los Angeles administrative and physical boundary layers for reproducible analysis and easy mapping. Optionally enrich any layer with 2020 Census demographics. Pinpoint "your LA" with an API.

## Purpose

Provides clean, versioned, well-documented boundary layers for LA city & county with:
- **Official sources** from open data portals maintained by LA city and LA County
- **Standardized outputs** in WGS84 (EPSG:4326)
- **Area calculations** using California Albers (EPSG:3310) for accuracy
- **Normalized schemas** with consistent lower_snake_case naming
- **Quality validation** with geometry checks and expected feature counts
- **Optional demographics** from 2020 Census via block-level apportionment

## Available layers

All layers available as clean GeoJSON with standardized fields, area calculations, and validation.

### Canonical LA neighborhoods

**The "Where do you live?" map for Los Angeles County**

- **LA neighborhoods** (270): Every city, unincorporated area, and LA City neighborhood in one layer
  - Includes incorporated cities (Inglewood, Pasadena, Culver City)
  - Unincorporated areas (Marina del Rey, East LA, Hacienda Heights)  
  - LA City neighborhoods (Venice, Silver Lake, North Hollywood)
  - This is what people mean when they say "I live in Hollywood" or "I'm in Culver City"
  - No, you don't live in the "City of North Hollywood"! 

**Source:** [LA Times Mapping LA project](https://github.com/datadesk/boundaries.latimes.com) (archived)  
**Credit:** Created by [Ben Welsh](https://github.com/palewire) and the [LA Times Data Desk](https://github.com/datadesk). Though the original project was deprecated a few years ago, I'm excited to keep these essential boundaries active — and easily enriched with demographic data — in my own way. 

### LAPD (police)
- **Bureaus** (4): Central, South, Valley, West
- **Divisions** (21): Pacific, Rampart, Central, etc.
- **Reporting Districts** (~1,191): Finest-grained LAPD geography
- **Station Locations** (21): Police station addresses and locations

### LA city
- **City Boundary**: Official city limits
- **Neighborhoods** (114): LA Times boundaries within LA City only (officially adopted)
- **Neighborhood Councils**: ~99 certified councils
- **Council Districts**: 15 city council districts
- **Parks**: 561 parks and recreation facilities

*For the complete county-wide map including all cities and unincorporated areas, see "LA Neighborhoods (Comprehensive)" above.*

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

---

## **+ Demographics available**

**All polygon layers can be enriched with 2020 Census demographics** (population, race/ethnicity, housing) through reproducible block-level apportionment.

**Option 1: Download pre-computed demographics** (fastest, no API key needed)
```bash
# Download all layers + demographics from S3
make s3-download
```

**Option 2: Compute demographics yourself** (reproducible pipeline)
```bash
# Get free API key from census.gov, then:
export CENSUS_API_KEY="your-key"
make fetch-census
make apportion-census
```

**Output:** Each layer gets a companion `*_demographics.parquet` file with population totals, race/ethnicity breakdowns, and housing counts from the 2020 Census.

**→** See [Census Demographics](#census-demographics-enrichment) section below for details.

---

## **+ Point-lookup API available**

**Query any coordinate to get all geographic information in one request** - Find neighborhood, city, police division, fire station, council district, and more for any lat/lon point.

**Live API endpoint:** `https://api.stilesdata.com/la-geography/lookup`

```bash
# Example: What's at this location?
curl "https://api.stilesdata.com/la-geography/lookup?lat=34.0665304&lon=-118.3718048"

# Response includes all layers
{
  "status": "success",
  "query": {
    "lat": 34.0665304,
    "lon": -118.3718048
  },
  "results": {
    "neighborhood": "Beverly Grove",
    "city": "Los Angeles",
    "lapd_division": "Wilshire",
    "lapd_bureau": "West Bureau",
    "lafd_station": "Fire Station 61",
    "lacofd_station": "N/A (LAFD jurisdiction)",
    "council_district": "5 - Katy Yaroslavsky",
    "neighborhood_council": "Mid City West CC",
    "school_district": "Los Angeles USD"
  }
}
```

**Deploy your own API** (AWS Lambda + API Gateway, ~$0.30/month for low traffic):
```bash
cd lambda/
sam build
sam deploy --guided
```

**→** See [API Documentation](docs/API.md) and [Deployment Guide](lambda/DEPLOYMENT.md) for details.

---

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

## S3 storage

Processed layers and demographics are published to S3 for public access:

```bash
# Upload all layers + demographics to S3
make s3-upload

# Download layers + demographics from S3 (if you just need the data)
make s3-download

# List available layers in S3
make s3-list

# Upload a single layer (with its demographics if available)
python scripts/s3_sync.py upload --layer la_city_boundary

# Upload boundaries only (skip demographics)
python scripts/s3_sync.py upload --no-demographics
```

**Direct download URLs:**

All layers are publicly accessible via HTTPS. Click layer names to download:

| Layer | Size |
|-------|------|
| [**LA neighborhoods (comprehensive)**](https://stilesdata.com/la-geography/la_neighborhoods_comprehensive.geojson) | **5.80 MB** |
| [LAPD bureaus](https://stilesdata.com/la-geography/lapd_bureaus.geojson) | 0.55 MB |
| [LAPD divisions](https://stilesdata.com/la-geography/lapd_divisions.geojson) | 0.84 MB |
| [LAPD reporting districts](https://stilesdata.com/la-geography/lapd_reporting_districts.geojson) | 6.50 MB |
| [LAPD station locations](https://stilesdata.com/la-geography/lapd_station_locations.geojson) | 0.01 MB |
| [LA city boundary](https://stilesdata.com/la-geography/la_city_boundary.geojson) | 0.40 MB |
| [LA city neighborhoods](https://stilesdata.com/la-geography/la_city_neighborhoods.geojson) | 0.95 MB |
| [LA city neighborhood councils](https://stilesdata.com/la-geography/la_city_neighborhood_councils.geojson) | 2.80 MB |
| [LA city council districts](https://stilesdata.com/la-geography/la_city_council_districts.geojson) | 1.40 MB |
| [LA city parks](https://stilesdata.com/la-geography/la_city_parks.geojson) | 5.00 MB |
| [LA County boundary](https://stilesdata.com/la-geography/la_county_boundary.geojson) | 2.80 MB |
| [LA County cities](https://stilesdata.com/la-geography/la_county_cities.geojson) | 13.53 MB |
| [LA County school districts](https://stilesdata.com/la-geography/la_county_school_districts.geojson) | 4.30 MB |
| [LA freeways](https://stilesdata.com/la-geography/la_freeways.geojson) | 1.62 MB |
| [LA Metro lines](https://stilesdata.com/la-geography/la_metro_lines.geojson) | 0.44 MB |
| [LA County Fire Dept station boundaries](https://stilesdata.com/la-geography/lacofd_station_boundaries.geojson) | 5.10 MB |
| [LA County Fire Dept station locations](https://stilesdata.com/la-geography/lacofd_station_locations.geojson) | 0.10 MB |
| [LA Fire Dept (city) station boundaries](https://stilesdata.com/la-geography/lafd_station_boundaries.geojson) | 1.70 MB |
| [Metadata](https://stilesdata.com/la-geography/metadata.json) | JSON |

**Demographics files:**  
Each polygon layer also has a companion demographics file available:
- Pattern: `https://stilesdata.com/la-geography/{layer}_demographics.parquet`
- Example: `https://stilesdata.com/la-geography/lapd_divisions_demographics.parquet`
- Size: Typically < 50 KB per layer

**Quick examples:**
```python
# Python with GeoPandas
import geopandas as gpd
import pandas as pd

# Load the comprehensive LA neighborhoods layer
neighborhoods = gpd.read_file('https://stilesdata.com/la-geography/la_neighborhoods_comprehensive.geojson')

# Load demographics (if available)
demographics = pd.read_parquet('https://stilesdata.com/la-geography/la_neighborhoods_comprehensive_demographics.parquet')

# Or load a simpler layer like city boundary
boundaries = gpd.read_file('https://stilesdata.com/la-geography/la_city_boundary.geojson')

# R with sf
library(sf)
library(arrow)
neighborhoods <- st_read('https://stilesdata.com/la-geography/la_neighborhoods_comprehensive.geojson')
demographics <- read_parquet('https://stilesdata.com/la-geography/la_neighborhoods_comprehensive_demographics.parquet')
```

```javascript
// JavaScript with D3
d3.json('https://stilesdata.com/la-geography/la_neighborhoods_comprehensive.geojson')
  .then(data => {
    const projection = d3.geoMercator().fitSize([width, height], data);
    const path = d3.geoPath().projection(projection);
    svg.selectAll('path').data(data.features)
       .enter().append('path')
         .attr('d', path)
         .attr('class', d => d.properties.type); // Style by city/neighborhood type
  });
```

**Environment setup:**
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
│   ├── census/            # Census blocks and demographics
│   └── docs/              # Generated maps and quicklooks
├── docs/                  # Documentation
│   ├── CENSUS_FIELDS.md   # Census variable definitions
│   ├── CENSUS_SETUP.md    # Census API key setup
│   ├── CENSUS_ANALYSIS.md # Analysis examples
│   └── CENSUS_TESTING.md  # Testing guide
├── scripts/
│   ├── fetch_boundaries.py        # Fetch boundary layers
│   ├── fetch_census.py            # Fetch Census data
│   ├── apportion_census.py        # Apportion demographics
│   ├── validate_apportionment.py  # Validate results
│   ├── analyze_demographics.py    # Analyze demographics (comprehensive)
│   ├── census_stats.py            # Quick demographics stats
│   ├── process_raw.py             # Process complex layers
│   ├── geo_utils.py               # Shared utilities
│   └── s3_sync.py                 # Upload/download from S3
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

## Data sources

- **LA City GeoHub**: https://geohub.lacity.org/
- **LA County GIS Hub**: https://egis-lacounty.hub.arcgis.com/
- **Caltrans**: https://caltrans-gis.dot.ca.gov/
- **LA Times Data Desk**: https://github.com/datadesk/boundaries.latimes.com (archived)

All sources are official government portals or trusted journalism organizations with open data licenses.

## Coordinate reference systems

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

## Census demographics enrichment

**Enrich any polygon layer with 2020 Census demographics** using reproducible, area-weighted block apportionment.

### What you get

From the 2020 Decennial Census (hard counts, not estimates):
- **Population totals** by race and Hispanic/Latino ethnicity
- **Housing units** (total, occupied, vacant)
- **Area-weighted apportionment** from Census blocks to your target polygons

**Available for all 13 polygon layers.** See [CENSUS_FIELDS.md](docs/CENSUS_FIELDS.md) for complete field documentation.

### Quick start

```bash
# 1. Get a free Census API key (one-time, 2 minutes)
#    Visit: https://api.census.gov/data/key_signup.html
export CENSUS_API_KEY="your-key-here"

# 2. Fetch LA County Census blocks (~2-3 minutes, ~254K blocks)
make fetch-census

# 3. Test with LAPD bureaus (fast, 4 features)
make apportion-census-test

# 4. Apportion to all layers (~5-10 minutes)
make apportion-census

# 5. Validate results
make validate-census
```

### Why separate files?

Demographics are stored as **companion Parquet files** (separate from GeoJSON boundaries) for several good reasons:

- **Size efficiency**: Demographics are ~50 KB vs 1-15 MB for geometries. Parquet is extremely compact for tabular data.
- **Optional enrichment**: Users who only need boundaries (for basemaps, spatial joins, etc.) don't download or process demographics.
- **Update independence**: Re-run census apportionment without re-fetching boundaries.
- **Data type optimization**: GeoJSON for geometry (human-readable, universal), Parquet for demographics (binary, columnar, fast).
- **Clear provenance**: Separation makes it explicit that demographics are derived, not intrinsic properties.

### Usage patterns

**Option 1: Helper function (recommended)**

The easiest way to load layers with demographics:

```python
from scripts.data_loader import load_layer_with_demographics

# Load boundaries + demographics in one line
enriched = load_layer_with_demographics('lapd_divisions')

# Works with local files or S3 URLs
enriched = load_layer_with_demographics(
    'lapd_divisions',
    base_url='https://stilesdata.com/la-geography'
)

# Map or analyze
enriched.plot(column='pop_total', legend=True, figsize=(12, 10))
```

**Option 2: Manual join (full control)**

For transparency or custom joins:

```python
import pandas as pd
import geopandas as gpd

# Load files separately
boundaries = gpd.read_file('data/standard/lapd_divisions.geojson')
demographics = pd.read_parquet('data/standard/lapd_divisions_demographics.parquet')

# Join on ID field (varies by layer - see config/layers.yml)
joined = boundaries.merge(demographics, on='prec')

# Calculate percentages
joined['pct_hispanic'] = joined['pop_hispanic'] / joined['pop_total'] * 100
```

**Option 3: Boundaries only**

Many use cases don't need demographics:

```python
import geopandas as gpd
from scripts.data_loader import load_layer

# Just the boundaries
boundaries = load_layer('lapd_divisions')

# Or from S3
boundaries = gpd.read_file('https://stilesdata.com/la-geography/lapd_divisions.geojson')
```

**R users:**

```r
library(sf)
library(arrow)
library(dplyr)

# Load and join
boundaries <- st_read('https://stilesdata.com/la-geography/lapd_divisions.geojson')
demographics <- read_parquet('https://stilesdata.com/la-geography/lapd_divisions_demographics.parquet')
enriched <- boundaries %>% left_join(demographics, by = 'prec')
```

### Demographic fields

Each `*_demographics.parquet` file includes:
- `pop_total`, `pop_hispanic`, `pop_white_nh`, `pop_black_nh`, `pop_asian_nh`, `pop_nhpi_nh`, `pop_aian_nh`, `pop_other_nh`, `pop_two_or_more_nh`
- `housing_total`, `housing_occupied`, `housing_vacant`
- `source_blocks_count`, `apportioned_at`, `census_vintage`

**Note:** These are 2020 Census hard counts (no margins of error). For income, education, or median age, you'll need American Community Survey (ACS) data.

### Analysis & examples

Quick statistics for any layer:
```bash
# Show demographics summary
python scripts/census_stats.py lapd_divisions

# Top 10 features by population
python scripts/census_stats.py la_city_neighborhoods --top 10
```

Comprehensive analysis:
```bash
# Analyze all layers
python scripts/analyze_demographics.py

# Analyze specific layer
python scripts/analyze_demographics.py --layer lapd_bureaus

# Generate markdown report
python scripts/analyze_demographics.py --save-report
```

### Documentation

- **Setup guide:** [CENSUS_SETUP.md](docs/CENSUS_SETUP.md)
- **Field definitions:** [CENSUS_FIELDS.md](docs/CENSUS_FIELDS.md)
- **Analysis examples:** [CENSUS_ANALYSIS.md](docs/CENSUS_ANALYSIS.md)
- **Testing guide:** [CENSUS_TESTING.md](docs/CENSUS_TESTING.md)