# Available layers from LA City & County portals

_Last updated: 2025-10-19_

## Summary

This document catalogs layers available from official LA City and County GIS portals that align with our project needs.

---

## LA City GeoHub (maps.lacity.org/lahub)

### LAPD Boundaries ✅
**Service**: `https://maps.lacity.org/lahub/rest/services/LAPD/MapServer`

| Layer | ID | Description | Features |
|-------|-----|-------------|----------|
| LAPD Stations | 0 | Police station locations | Points |
| LAPD Bureaus | 2 | 4 bureaus (Central, South, Valley, West) | Polygons |
| LAPD Divisions | 3 | 21 divisions (Central, Rampart, Southwest, etc.) | Polygons |
| LAPD Reporting Districts | 4 | ~1,191 reporting districts | Polygons |

**Alternative endpoints** (FeatureServer, already in your scripts):
- Bureaus: `https://services5.arcgis.com/7nsPwEMP38bSkCjy/ArcGIS/rest/services/LAPD_Bureaus/FeatureServer/0`
- Divisions: `https://services5.arcgis.com/7nsPwEMP38bSkCjy/arcgis/rest/services/LAPD_Division/FeatureServer/0`
- Reporting Districts: `https://services5.arcgis.com/7nsPwEMP38bSkCjy/arcgis/rest/services/LAPD_Reporting_District/FeatureServer/0`

### City boundaries & administrative
**Service**: `https://maps.lacity.org/lahub/rest/services/Boundaries/MapServer`

| Layer | ID | Description | Official |
|-------|-----|-------------|----------|
| City Boundary | 7 | LA City boundary | ✅ |
| County Boundary | 15 | LA County boundary | ✅ |
| Neighborhood Councils (Certified) | 18 | Official neighborhood councils (~99 councils) | ✅ |
| Council Districts | 13 | 15 city council districts | ✅ |
| Community Plan Areas | 9 | Planning areas | ✅ |
| Adjacent Cities | 1 | Neighboring cities | ✅ |

**Full Boundaries MapServer URL**: `https://maps.lacity.org/lahub/rest/services/Boundaries/MapServer`

### LA City neighborhoods - LA Times boundaries ✅
**Hub Page**: https://geohub.lacity.org/datasets/lahub::la-times-neighborhood-boundaries/about

The City of Los Angeles has officially adopted the LA Times neighborhood boundaries. This is different from "Community Plan Areas" (which are planning zones).

**REST Endpoint** (to be confirmed via Hub page): Likely on LA City GeoHub MapServer or FeatureServer
- Search for "LA Times" or "Times Neighborhood" in LA City services

---

## LA County GIS Hub (egis-lacounty.hub.arcgis.com)

### County boundaries & cities ✅
**Service**: `https://public.gis.lacounty.gov/public/rest/services/LACounty_Dynamic/Political_Boundaries/MapServer`

| Layer | ID | Description | Official | Fields |
|-------|-----|-------------|----------|--------|
| County Boundaries | 18 | LA County boundary (includes neighboring counties) | ✅ | TYPE ('LA County', 'Other County'), NAME |
| City Boundaries | 19 | All incorporated cities in LA County | ✅ | CITY_COMM_NAME, JURISDICTION |
| Community Boundaries (CSA) | 23 | Unincorporated communities | ✅ | (Census Service Areas) |

**Note**: Layer 19 (City Boundaries) includes both incorporated cities AND unincorporated communities, distinguished by the `JURISDICTION` field ('INCORPORATED CITY' vs 'UNINCORPORATED AREA')

**Alternative source from LA County Planning**:
- Hub: https://egis-lacounty.hub.arcgis.com/datasets/city-and-unincorporated-community-boundary-la-county-planning
- Includes comprehensive update history and field: `CITY_COMM_NAME`

### Public works data
**Service**: `https://dpw.gis.lacounty.gov/dpw/rest/services/PW_Open_Data/MapServer`

| Layer | ID | Description | Type |
|-------|-----|-------------|------|
| DPW_CITY_BOUNDARIES | 43 | City boundaries | Polygons |
| DPW_COUNTY_BOUNDARY | 13 | County boundary | Polygon |
| Bikeways | 50 | LA County bikeways | Lines |

---

## Freeways / Highways

### Caltrans - California National Highway System
**Service**: `https://caltrans-gis.dot.ca.gov/arcgis/rest/services/chhighway/national_highway_system/featureserver/0`

| Layer | Description | Categories |
|-------|-------------|------------|
| NHS | National Highway System for California | Interstate, Other NHS, STRAHNET, etc. |

**Note**: Covers entire state. Will need to clip to LA County extent.

### LA County DPW street network
**Service**: `https://dpw.gis.lacounty.gov/dpw/rest/services/GMED_LACounty_StreetMap/MapServer`

Includes:
- Freeway and Highway Shields (Layer 85)
- Roads at multiple scale levels (47+)
- Building footprints, parks, etc.

---

## Comparison with existing script URLs

Your `fetch_boundaries.py` currently uses these sources:

| Layer | Your Source | Official Alternative |
|-------|-------------|---------------------|
| LA City Boundary | S3 bucket (stilesdata.com) | ✅ LA City GeoHub Layer 7 |
| LA County Boundary | maps.lacity.org/lahub/.../MapServer/15 | ✅ Same or LA County Hub |
| LA County neighborhoods | S3 bucket | ❓ Need to identify official source |
| LA City neighborhoods | S3 bucket | ❓ Community Plan Areas (Layer 9)? |
| LAPD Bureaus | services5.arcgis.com | ✅ Same (official) |
| LAPD Divisions | services5.arcgis.com | ✅ Same (official) |
| LAPD Reporting Districts | services5.arcgis.com | ✅ Same (official) |

---

## Recommendations

### Priority 1: Replace S3 sources with official endpoints ✅
1. ✅ **LA City Boundary**: `https://maps.lacity.org/lahub/rest/services/Boundaries/MapServer/7`
2. ✅ **LA County Boundary**: `https://public.gis.lacounty.gov/public/rest/services/LACounty_Dynamic/Political_Boundaries/MapServer/18`
3. ✅ **LA City Neighborhoods**: LA Times boundaries (user confirmed) - find FeatureServer endpoint
4. ✅ **LA County Cities + Unincorporated**: `https://public.gis.lacounty.gov/public/rest/services/LACounty_Dynamic/Political_Boundaries/MapServer/19`

### Priority 2: Add missing layers from PLANNING.md
5. ✅ **Neighborhood Councils**: `https://maps.lacity.org/lahub/rest/services/Boundaries/MapServer/18`
6. ✅ **Freeways**: Use Caltrans NHS layer, **clip to LA County boundary** - `https://caltrans-gis.dot.ca.gov/arcgis/rest/services/chhighway/national_highway_system/FeatureServer/0`

### Remaining task
1. Find the exact REST endpoint for LA Times Neighborhood Boundaries (check GeoHub item page for FeatureServer URL)

---

## Next steps

1. Create `config/layers.yml` with these official endpoints
2. Update fetch scripts to use official sources
3. Test each layer to verify feature counts and schemas
4. Document field mappings for standardization

