# Census demographic fields

Documentation for 2020 Decennial Census variables included in this repository's demographic enrichment.

**Last updated:** 2025-10-25  
**Census vintage:** 2020 Decennial Census (PL 94-171 Redistricting File)  
**Geography:** Census blocks, apportioned to polygon layers  
**Coverage:** Los Angeles County, California

---

## Overview

This repository includes demographic data from the 2020 Decennial Census, apportioned from Census blocks to various administrative and geographic boundaries. The data comes from the **PL 94-171 Redistricting Data Summary File**, which contains hard counts (not estimates) of population and housing.

### Why decennial census?

The Decennial Census provides:
- **Hard counts** (not sample-based estimates)
- **No margins of error** (unlike American Community Survey)
- **Complete enumeration** of all persons and housing units
- **Block-level geography** (finest available)

### What's NOT included

The Decennial Census does **not** include:
- Median age or age distributions (beyond voting age 18+)
- Income, poverty, or economic data
- Education levels
- Language spoken at home
- Disability status
- Employment or occupation

*For these variables, you need the American Community Survey (ACS), which has margins of error and coarser geography (typically block group or tract level).*

---

## Apportionment methodology

Census demographic values are **area-weighted** from Census blocks to target polygons:

1. **Intersect** Census blocks with target polygon boundaries
2. **Calculate** the intersection area for each block-polygon pair
3. **Weight** each demographic value by the proportion of block area in each polygon
4. **Sum** weighted values for all blocks within each target polygon

**CRS for area calculation:** EPSG:3310 (California Albers, equal-area projection)

### Example

If a Census block with 100 people is split:
- 75% of block area in Target A → 75 people apportioned to A
- 25% of block area in Target B → 25 people apportioned to B

### Caveats

1. **Assumes uniform population distribution within blocks** - Not always accurate (e.g., blocks with parks, industrial areas, or clustered housing)
2. **Group quarters** (dorms, prisons, nursing homes) may create localized concentrations
3. **Water and uninhabited areas** are included in block areas, potentially diluting density
4. **Boundary slivers** from spatial joins may cause small (~0.1%) discrepancies in totals
5. **Recent growth** since 2020 is not reflected

---

## Field definitions

All fields are integer counts (whole numbers).

### Population Fields

| Field Name | Description | Census Variable | Notes |
|------------|-------------|-----------------|-------|
| `pop_total` | Total population | P1_001N | All persons enumerated in Census |
| `pop_hispanic` | Hispanic or Latino (any race) | P2_002N | Ethnicity, not race |
| `pop_not_hispanic` | Not Hispanic or Latino | P2_003N | Sum of all non-Hispanic race categories |
| `pop_white_nh` | White alone, not Hispanic | P2_005N | Single race category |
| `pop_black_nh` | Black or African American alone, not Hispanic | P2_006N | Single race category |
| `pop_aian_nh` | American Indian and Alaska Native alone, not Hispanic | P2_007N | Single race category |
| `pop_asian_nh` | Asian alone, not Hispanic | P2_008N | Single race category |
| `pop_nhpi_nh` | Native Hawaiian and Pacific Islander alone, not Hispanic | P2_009N | Single race category |
| `pop_other_nh` | Some Other Race alone, not Hispanic | P2_010N | Single race category |
| `pop_two_or_more_nh` | Two or More Races, not Hispanic | P2_011N | Multiple race categories |

**Race and ethnicity:**
- Hispanic/Latino is an **ethnicity**, not a race
- A person can be Hispanic + any race (White Hispanic, Black Hispanic, etc.)
- Non-Hispanic (`_nh` suffix) categories are mutually exclusive
- `pop_total` = `pop_hispanic` + `pop_not_hispanic`
- `pop_not_hispanic` = sum of all `_nh` categories

### Housing Fields

| Field Name | Description | Census Variable | Notes |
|------------|-------------|-----------------|-------|
| `housing_total` | Total housing units | H1_001N | All housing structures |
| `housing_occupied` | Occupied housing units | H1_002N | Has usual residents |
| `housing_vacant` | Vacant housing units | H1_003N | Unoccupied at time of Census |

**Housing notes:**
- `housing_total` = `housing_occupied` + `housing_vacant`
- Occupied = has residents on Census Day (April 1, 2020)
- Vacant includes seasonal, for rent, for sale, foreclosed, etc.

### Metadata Fields

| Field Name | Description |
|------------|-------------|
| `source_blocks_count` | Number of Census blocks apportioned to this feature |
| `apportioned_at` | ISO timestamp when apportionment was performed |
| `census_vintage` | Census year (2020) |
| `source_layer` | Name of the target polygon layer |

---

## Data sources

### Census block geometries

- **Source:** U.S. Census Bureau TIGER/Line Shapefiles
- **Product:** 2020 TIGER/Line Shapefiles - Blocks
- **Downloaded via:** `pygris` Python library
- **URL:** https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html

### Demographic data

- **Source:** U.S. Census Bureau 2020 Census Redistricting Data (PL 94-171)
- **Downloaded via:** Census API (https://api.census.gov/data/2020/dec/pl)
- **API Documentation:** https://www.census.gov/data/developers/data-sets/decennial-census.html

---

## Known 2020 Census benchmarks (LA County)

Use these for validation:

| Geography | Population | Housing Units |
|-----------|------------|---------------|
| **Los Angeles County** | 10,014,009 | 3,591,981 |
| **City of Los Angeles** | 3,898,747 | 1,498,964 |

Source: [2020 Census Redistricting Data](https://data.census.gov/)

---

## Census block summary (LA County)

- **Total blocks:** ~254,000
- **Population range:** 0 to ~2,000+ per block (most blocks < 200)
- **Area range:** 0.0001 to 100+ square miles (most blocks < 0.1 sq mi)
- **Zero-population blocks:** ~30-40% (parks, industrial, water, uninhabited)

---

## Usage examples

### Load apportioned demographics

```python
import pandas as pd
import geopandas as gpd

# Option 1: Demographics only (no geometry)
demo = pd.read_parquet('data/standard/lapd_divisions_demographics.parquet')

# Option 2: Join with boundaries
boundaries = gpd.read_file('data/standard/lapd_divisions.geojson')
demo = pd.read_parquet('data/standard/lapd_divisions_demographics.parquet')
joined = boundaries.merge(demo, on='prec')
```

### Calculate derived statistics

```python
# Hispanic percentage
demo['pct_hispanic'] = demo['pop_hispanic'] / demo['pop_total'] * 100

# Occupancy rate
demo['occupancy_rate'] = demo['housing_occupied'] / demo['housing_total'] * 100

# Non-Hispanic white share
demo['pct_white_nh'] = demo['pop_white_nh'] / demo['pop_total'] * 100
```

### Aggregate to larger geographies

```python
# Example: Sum neighborhood data to council districts
neighborhoods = pd.read_parquet('data/standard/la_city_neighborhoods_demographics.parquet')

# Assume neighborhoods have a 'council_district' field
by_district = neighborhoods.groupby('council_district')[
    ['pop_total', 'pop_hispanic', 'pop_white_nh', 'pop_black_nh', 
     'housing_total', 'housing_occupied']
].sum()
```

---

## References

- **Census Bureau PL 94-171 documentation:** https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html
- **Technical Documentation:** https://www2.census.gov/programs-surveys/decennial/2020/technical-documentation/
- **Variable Definitions:** https://api.census.gov/data/2020/dec/pl/variables.html

---

## License

Census data is public domain (U.S. government work). No restrictions on use or redistribution.

**Attribution:** U.S. Census Bureau, 2020 Decennial Census Redistricting Data (PL 94-171)

---

## Questions or issues?

See the main [README.md](../README.md) for repository information and contact details.

