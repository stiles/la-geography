
LA Geography planning doc

_Last updated: 2025-10-19_

## Purpose

Create a single, dependable repo of Los Angeles administrative and physical boundary layers for quick reference and reproducible analysis across apps and stories. Each layer is **clean**, **versioned**, **documented**, and includes basic normalizations like area in square miles. Longer term, attach apportioned 2020 Census demographics at multiple geographies.

## Guiding principles

- Prefer official sources over convenience mirrors
- Keep outputs WGS84 for sharing, use a local equal-area proj for measurement
- Cache raw, never mutate in place
- Small, sharp scripts over one mega notebook
- Clear lineage, clear licenses, clear dates
- Standardized, lower_case column headers and naming conventions (where possible) across all boundaries
- Ship minimal first, then enrich deliberately
- Use uv for dependencies/virtualenv
- Use s3 for storage and built that into workflow
- Comprehensive documention lising fields, sources, etc., for each layer as a reference for users

## Name and scope

Working name: **la-geo** (short, searchable). Alternatives: `geo-la`, `la-maps`.

Scope starts with LA City & County footprint and LAPD geographies, plus a freeway line layer. More layers can join if they meet the same quality bar.

## Initial layers

- LAPD bureaus
- LAPD divisions
- LAPD reporting districts
- LA city boundary
- LA county boundary
- LA county cities and unincorporated areas
- LA city neighborhood boundaries
- LA city neighborhood council boundaries
- LA area freeways

## Sources of truth

- LA City GeoHub: https://geohub.lacity.org/datasets/
- LA County GIS Hub: https://egis-lacounty.hub.arcgis.com/
- ArcGIS REST Feature/Map Servers discovered from those hubs

## Outputs (contract)

Each published layer in `data/standard/` is GeoJSON and Parquet with:

- `geometry` in EPSG:4326
- lower_snake_case fields
- `area_sqmi` for polygons
- `source_url`, `source_layer`, `source_version` if available
- `fetched_at` ISO timestamp
- optional `bbox` string for quick sanity checks

## Directory layout

```
la-geo/
  README.md
  PLANNING.md
  data/
    raw/                # immutable pulls
    standard/           # cleaned + normalized
    docs/               # sample maps, quicklooks
  scripts/
    fetch_boundaries.py
    fetch_lapd_boundaries.py
    enrich_area.py
    census_apportion.py
    validate.py
  config/
    layers.yml          # endpoints, ids, expected counts, key fields
  tests/
    test_validate.py
  Makefile
```

## Minimal pipeline

1) **Fetch** raw layers from ArcGIS REST or direct GeoJSON using `ezesri`
2) **Standardize** CRS, field names, id columns, and compute `area_sqmi`
3) **Validate** counts, geometry validity, extents, and basic hierarchy checks
4) **Export** to GeoJSON + Parquet with metadata sidecars
5) **Enrich (optional)** block-level Census apportionments to targets

### CRS policy

- Storage & interchange: **EPSG:4326**
- Metrics (area, length): **EPSG:3310** (California Albers) to avoid Web Mercator distortion

```python
# area helper (polygons)
def area_sqmi(gdf):
    metr = gdf.to_crs(3310)  # California Albers (meters)
    return metr.area / 2_589_988.110336  # m² to mi²
```

### Fetch with ezesri

Use `ezesri.extract_layer()` under the hood. Keep endpoints in `config/layers.yml` so swaps are edits not code changes.

```bash
# examples
python scripts/fetch_boundaries.py --out data/raw/
python scripts/fetch_lapd_boundaries.py --out data/raw/
```

```python
# thin wrapper inside fetch scripts
import ezesri, geopandas as gpd

def fetch_arcgis(url: str) -> gpd.GeoDataFrame:
    gdf = ezesri.extract_layer(url)
    gdf.columns = gdf.columns.str.lower().str.strip()
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)
    return gdf
```

### Standardize & normalize

- rename ids: `bureau`, `division`, `rd` for LAPD layers
- `name` as the canonical label field when present
- compute `area_sqmi` for polygonal layers
- preserve authoritative ids (e.g., `geoid`, `juris_id`) as `source_id_*`

```python
# quick normalizer sketch
def standardize(gdf, id_map=None):
    gdf.columns = gdf.columns.str.lower().str.strip()
    if id_map:
        gdf = gdf.rename(columns=id_map)
    gdf["area_sqmi"] = area_sqmi(gdf) if gdf.geom_type.isin(["Polygon","MultiPolygon"]).any() else None
    return gdf
```

## Validation

Fast checks that fail loud:

- nonempty features, no null geometries
- valid geometries after `buffer(0)` fix attempt
- expected feature counts within tolerance
- bbox inside LA County
- LAPD hierarchy sanity: districts ≥ divisions ≥ bureaus
- no duplicated ids

```python
def bbox_ok(gdf):
    minx, miny, maxx, maxy = gdf.total_bounds
    # rough LA County bounds
    return (-119.1 < minx < -116.9) and (33.3 < miny < 35.0)

def fix_geoms(gdf):
    gdf["geometry"] = gdf.buffer(0)
    return gdf
```

Run with `make validate` to gate exports.

## Census enrichment (phase 2)

Goal: attach apportioned 2020 block demographics to target geographies.

- pull 2020 blocks + attributes from Census TIGER & Decennial tables
- intersect blocks with targets in 3310
- weighted sums by area overlap for additive fields
- store results as separate Parquet joined by target id
- document margin of error assumptions and caveats

```python
# simplistic apportion sketch
def apportion(blocks, targets, value_cols):
    b = blocks.to_crs(3310)
    t = targets.to_crs(3310)
    inter = gpd.overlay(b, t, how="intersection")
    inter["a"] = inter.area
    frac = inter["a"] / inter.groupby("block_geoid")["a"].transform("sum")
    for c in value_cols:
        inter[f"{c}_w"] = inter[c] * frac
    sums = inter.groupby("target_id")[[f"{c}_w" for c in value_cols]].sum().reset_index()
    return sums
```

## Make targets

```
make fetch          # pulls raw layers listed in config/layers.yml
make standardize    # cleans + adds area
make validate       # runs geometry and count checks
make export         # writes GeoJSON + Parquet in data/standard
make quicklook      # dumps small PNGs for eyeballing
```

## Metadata & licensing

Each layer gets a `{layer}.meta.json` with `source_url`, `copyright`, `license`, `fetch_method`, `fetched_at`, `fields`. Copy license and attribution from the hub pages. If licensing is murky, note it and avoid redistribution beyond internal use.

## Testing

- unit tests for helpers (area, bbox, id normalization)
- smoke tests hitting one small layer per source to catch upstream changes
- Golden counts snapshot to detect surprise deltas

## Roadmap

**Phase 0** — repo bootstrap, config, Makefile, two fetch scripts  
**Phase 1** — LAPD + city/county layers, standardize, validate, export  
**Phase 2** — block-level apportion for a small pilot layer  
**Phase 3** — docs site with layer gallery and data dictionary
**Phase 4** — scheduled refreshes with change logs

## Risks and realities

ArcGIS endpoints move or change schemas without warning. Counts shift after annexations or QA passes. Solve with config-driven fetches, pinned snapshots in `data/raw/`, and validation that screams when something drifts.

## Quick start

```bash
uv venv && source .venv/bin/activate
uv add geopandas shapely pyproj pyarrow ezesri
make fetch standardize validate export
```

## Notes on the included scripts

You already have `fetch_boundaries.py` and `fetch_lapd_boundaries.py`. Keep them, but switch area calculation to EPSG:3310, move endpoint configs into `config/layers.yml`, and wire `make` targets so the happy path is one command.
