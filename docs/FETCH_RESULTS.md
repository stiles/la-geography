# Fetch Results & Issues

_Created: 2025-10-19_

## Summary

Fetched **9 layers** from official sources. **6 layers are clean**, **3 layers need work**.

---

## ✅ Clean Layers (6)

These layers are ready to use with minimal or no processing:

### LAPD Layers
| Layer | Features | Status | Notes |
|-------|----------|--------|-------|
| **lapd_bureaus** | 4 | ✅ Perfect | 4 bureaus, clean schema |
| **lapd_divisions** | 21 | ✅ Perfect | 21 divisions, clean schema |
| **lapd_reporting_districts** | 1,191 | ✅ Perfect | 1 invalid geometry auto-fixed |

**Validation**: LAPD hierarchy is correct (1,191 districts ≥ 21 divisions ≥ 4 bureaus)

### LA City Layers
| Layer | Features | Status | Notes |
|-------|----------|--------|-------|
| **la_city_boundary** | 1 | ✅ Perfect | Single feature, 478.25 sq mi |
| **la_city_neighborhoods** | 114 | ✅ Perfect | LA Times boundaries, 1 invalid geom fixed |
| **la_city_neighborhood_councils** | 99 | ✅ Perfect | Certified councils, 4 invalid geoms fixed |

---

## ⚠️ Layers Needing Work (3)

### 1. LA County Boundary
**Issue**: Contains **11 features** (neighboring counties included) instead of 1

**Current state:**
```
Features: 11 (expected: 1)
Bounds: (-121.29, 32.52) to (-116.22, 35.79)  # Extends far beyond LA County
Area range: 56.38 - 9828.86 sq mi
```

**What's in there:**
- **3 LA County pieces** (TYPE = 'LA County'):
  - 3,953.83 sq mi (mainland)
  - 74.57 sq mi (Catalina Island)
  - 56.38 sq mi (San Clemente Island)
  - **Total: 4,084.78 sq mi** ✅ Correct!
  
- **8 neighboring counties** (TYPE = 'Other County'):
  - San Bernardino (9,828 sq mi)
  - Kern (8,088 sq mi)
  - San Diego, Riverside, Ventura, Orange, etc.

**Required fix:**
```python
# Filter to LA County only
gdf = gdf[gdf['type'] == 'LA County']

# Dissolve the 3 pieces into 1 feature
gdf = gdf.dissolve()
```

**Result**: 1 feature, 4,084.78 sq mi

---

### 2. LA County Cities & Unincorporated Areas
**Issue**: Contains **347 fragments** instead of ~88 distinct cities/communities

**Current state:**
```
Features: 347 (expected: 88)
Bounds: (-118.94, 32.80) to (-117.65, 34.82)  # Includes islands
Area range: 0.00 - 2215.81 sq mi
```

**What's in there:**
- **157 city fragments** (city_type = 'City')
- **190 unincorporated fragments** (city_type = 'Unincorporated')

**Issues:**
1. **Fragmentation** - Multiple polygons per city/community
   - Example: "Los Angeles" has 469.89 sq mi as one feature (likely the main piece)
   - But probably has other fragments elsewhere
   
2. **Huge unincorporated area** - Single "Unincorporated" polygon of 2,215 sq mi
   - This is ~54% of LA County's total area!
   - Likely combines many separate unincorporated communities
   
3. **Tiny slivers** - Features as small as 0.000011 sq mi (~300 sq ft)
   - These are likely data quality issues or border fragments

**Possible fixes:**

**Option A - Dissolve by name:**
```python
# Merge all fragments with same city_name
gdf = gdf.dissolve(by='city_name', aggfunc='first')
```
Result: ~88 features (one per city/community)

**Option B - Keep fragments but add identifier:**
```python
# Add a group ID for same city/community
gdf['city_id'] = gdf.groupby('city_name').ngroup()
```
Result: 347 features but with clear grouping

**Option C - Use alternative source:**
- Look for a different LA County cities layer with pre-aggregated features
- The current layer may be designed for parcel-level analysis

**Recommendation**: Try Option A first, but examine results carefully. The massive "Unincorporated" polygon is concerning.

---

### 3. LA Freeways
**Issue**: Statewide California data, needs clipping to LA County

**Current state:**
```
Features: 5,430 (entire California)
Bounds: (-124.22, 32.54) to (-114.49, 42.01)  # Oregon border to Mexico border
```

**What's in there:**
- Entire California National Highway System
- Interstate, Other NHS, STRAHNET, Connectors, etc.

**Required fix:**
```python
# Load LA County boundary (after fixing it)
county = gpd.read_file('data/standard/la_county_boundary.geojson')

# Clip freeways to county boundary
freeways_clipped = gpd.clip(freeways, county)
```

**Expected result**: ~50-150 freeway segments within LA County

**Notes:**
- This is expected behavior per PLANNING.md
- Clipping is standard operation
- May want small buffer (0.1 mi?) to catch freeways right at border

---

## Processing Pipeline Recommendations

### Phase 1: Filter & Dissolve (High Priority)
Create `scripts/process_raw.py` to handle:
1. **LA County Boundary** - Filter `TYPE == 'LA County'` + dissolve
2. **LA Freeways** - Clip to LA County boundary
3. **LA County Cities** - Dissolve by `city_name` (with care)

### Phase 2: Validation
Update `scripts/validate.py` to check:
- Feature counts match expected
- Geometries are valid
- Areas sum to reasonable totals
- No duplicate names (after dissolving)

### Phase 3: Standardization
Create `scripts/standardize.py` to:
- Normalize field names consistently
- Select/rename key fields
- Add standard metadata
- Export to Parquet + GeoJSON

---

## Field Analysis

### Fields to Normalize/Keep

**LAPD Layers:**
- Key fields: `bureau`, `prec` (division number), `repdist`, `aprec` (division name)
- Remove: `shape__area`, `shape__length` (redundant with `area_sqmi`)

**LA City Layers:**
- Key fields: `name` (for neighborhoods), varies for councils
- Very clean schemas, minimal cleanup needed

**LA County Layers:**
- Boundary: Just need `name` = "Los Angeles County"
- Cities: Key fields: `city_name`, `city_type`, `city_label`

**Freeways:**
- Key fields: `routeid`, `nhs_type` (Interstate, O-NHS, etc.)
- Remove after clipping: Segments outside LA County

---

## Next Steps

**Immediate:**
1. ✅ Create `scripts/process_raw.py` with filtering/dissolving logic
2. Test processing on the 3 problematic layers
3. Verify results (feature counts, areas, geometries)

**Short-term:**
4. Complete validation script
5. Standardize field names across all layers
6. Export to final `data/standard/` directory

**Questions to resolve:**
- How should we handle the huge "Unincorporated" area in cities layer?
- Is fragmentation an issue for cities, or is it acceptable?
- Should we filter out tiny slivers (< 0.01 sq mi)?

