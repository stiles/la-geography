# LA Regions Layer

Broad geographic regions of LA County, created by dissolving the comprehensive LA Times neighborhoods by their `region` field.

## Overview

The `la_regions` layer provides 16 high-level geographic regions covering all of LA County. These regions are useful for:
- High-level demographic analysis
- Understanding LA's major geographic areas
- Settling debates about which neighborhoods belong to which region (looking at you, Westside*)

## Data source

Derived from `la_neighborhoods_comprehensive` (LA Times Data Desk) by dissolving on the `region` field.

## Processing

Created using `scripts/process_raw.py --layer la_regions`:
1. Reads the comprehensive neighborhoods file (270 features)
2. Dissolves by the `region` field
3. Creates clean slug and name fields
4. Outputs 16 regional features

## Files

- `data/standard/la_regions.geojson` - Boundary geometries
- `data/standard/la_regions_demographics.parquet` - Census demographics (2020)

## Regions

| Region | Population | Area (sq mi) | Density (per sq mi) |
|--------|------------|--------------|---------------------|
| San Fernando Valley | 1,565,464 | 232.24 | 6,740.8 |
| San Gabriel Valley | 1,455,350 | 292.25 | 4,979.8 |
| Southeast | 1,173,342 | 133.83 | 8,767.7 |
| Harbor | 902,900 | 191.98 | 4,703.1 |
| Central LA | 843,376 | 63.68 | 13,244.3 |
| South LA | 815,312 | 51.08 | 15,962.9 |
| South Bay | 763,822 | 105.50 | 7,240.0 |
| Westside | 582,219 | 100.19 | 5,811.2 |
| Verdugos | 464,969 | 90.02 | 5,165.4 |
| Antelope Valley | 413,062 | 1,170.11 | 353.0 |
| Northwest County | 294,832 | 683.12 | 431.6 |
| Eastside | 272,793 | 20.66 | 13,202.7 |
| Pomona Valley | 225,908 | 49.42 | 4,571.3 |
| Northeast LA | 154,044 | 17.22 | 8,945.3 |
| Santa Monica Mountains | 82,334 | 162.34 | 507.2 |
| Angeles Forest | 4,124 | 662.56 | 6.2 |

**Total LA County: 10,013,851 people across 4,026.18 sq mi**

## Usage

```python
from scripts.data_loader import load_layer, load_layer_with_demographics

# Load boundaries only
regions = load_layer('la_regions')

# Load with demographics
regions_demo = load_layer_with_demographics('la_regions')

# Find which region contains a point
point_lon, point_lat = -118.2437, 34.0522  # Downtown LA
regions['contains_point'] = regions.geometry.contains(Point(point_lon, point_lat))
region = regions[regions['contains_point']].iloc[0]
print(f"Point is in: {region['name']}")
```

## Field reference

| Field | Type | Description |
|-------|------|-------------|
| `slug` | string | URL-safe identifier (e.g., 'san-fernando-valley') |
| `name` | string | Display name (e.g., 'San Fernando Valley') |
| `area_sqmi` | float | Area in square miles |
| `geometry` | geometry | Polygon geometry (WGS84) |

### Demographics fields (when loaded with demographics)

All demographic fields from 2020 Decennial Census:
- `pop_total` - Total population
- `pop_hispanic` - Hispanic or Latino population
- `pop_not_hispanic` - Not Hispanic or Latino
- `pop_white_nh` - White alone (not Hispanic)
- `pop_black_nh` - Black or African American alone (not Hispanic)
- `pop_asian_nh` - Asian alone (not Hispanic)
- `pop_aian_nh` - American Indian and Alaska Native alone (not Hispanic)
- `pop_nhpi_nh` - Native Hawaiian and Pacific Islander alone (not Hispanic)
- `pop_other_nh` - Some other race alone (not Hispanic)
- `pop_two_or_more_nh` - Two or more races (not Hispanic)
- `housing_total` - Total housing units
- `housing_occupied` - Occupied housing units
- `housing_vacant` - Vacant housing units

## Configuration

Defined in `config/layers.yml`:

```yaml
la_regions:
  source: derived
  derived_from: la_neighborhoods_comprehensive
  expected_count: 16
  geometry_type: polygon
  id_field: slug
  name_field: name
  source_org: LA Times Data Desk (derived)
```

## Integration

The layer integrates with the standard project workflow:

```bash
# Regenerate from raw data
make standardize

# Apportion census data
make apportion-census

# Upload to S3
make s3-upload
```

## Notes

* For people who think the Westside is only west of the 405, this layer shows the full Westside region as defined by the LA Times, which includes neighborhoods on both sides of the freeway. The Westside region covers 100.19 square miles with a population of 582,219 (2020 Census).

