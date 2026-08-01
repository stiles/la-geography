# API implementation notes

Internal documentation for LA Geography point-lookup API implementation decisions and enhancements.

## Governance/type context fields

**Added**: 2025-11-30

### Problem

The frontend needs to distinguish between different types of places in LA County to render appropriate labels:
- "Beverly Grove" is a neighborhood in the City of LA → "Neighborhood (City of LA)"
- "Pasadena" is a standalone city → "City" (don't show redundant neighborhood)
- "Marina del Rey" is unincorporated → "Unincorporated area — Los Angeles County"

Without this context, we risk fake interpretations like "City of North Hollywood".

### Solution

Add governance/type fields from the raw data to the API response so the frontend can make informed rendering decisions.

### New fields in API response

All fields added under `results`:

#### `neighborhood_type`
Type from `la_neighborhoods_comprehensive.geojson`:
- `"segment-of-a-city"` - Part of a larger city (e.g., "Beverly Grove" in LA)
- `"standalone-city"` - Independent incorporated city (e.g., "Pasadena")
- `"unincorporated-area"` - Unincorporated community (e.g., "Marina del Rey")
- `null` - No neighborhood match

#### `neighborhood_city_slug`
Raw `city` value from neighborhoods layer:
- `"los-angeles"` - LA City neighborhood
- Other city slug - Neighborhood in another city
- `null` - Standalone city or unincorporated area

#### `place_category`
Derived category for easy frontend rendering:
- `"la_city_neighborhood"` - Neighborhood in City of LA
  - Condition: `type == "segment-of-a-city" AND city == "los-angeles"`
  - Example: Beverly Grove, Downtown, Venice
  
- `"standalone_city"` - Independent city
  - Condition: `type == "standalone-city"`
  - Example: Pasadena, Santa Monica, Burbank
  
- `"unincorporated_area"` - Unincorporated community
  - Condition: `type == "unincorporated-area"`
  - Example: Marina del Rey, East LA, Hacienda Heights
  
- `null` - No match or indeterminate

#### `city_is_incorporated` (optional)
Boolean from `la_county_cities` layer:
- `true` - Incorporated city
- `false` - Unincorporated area (city_name == "Unincorporated")
- Not present if no city match

### Implementation

```python
def add_governance_context(results, matched_features):
    # Extract from neighborhoods layer
    if "la_neighborhoods_comprehensive" in matched_features:
        props = matched_features["la_neighborhoods_comprehensive"]
        
        n_type = props.get('type')
        n_city = props.get('city')
        
        results['neighborhood_type'] = n_type
        results['neighborhood_city_slug'] = n_city
        
        # Derive place category
        if n_type == 'segment-of-a-city' and n_city == 'los-angeles':
            results['place_category'] = 'la_city_neighborhood'
        elif n_type == 'standalone-city':
            results['place_category'] = 'standalone_city'
        elif n_type == 'unincorporated-area':
            results['place_category'] = 'unincorporated_area'
        else:
            results['place_category'] = None
    
    # Extract from cities layer
    if "la_county_cities" in matched_features:
        city_props = matched_features["la_county_cities"]
        city_type = city_props.get('city_type', '')
        city_name = city_props.get('city_name', '')
        
        results['city_is_incorporated'] = (
            city_type == 'City' and 
            city_name != 'Unincorporated'
        )
    
    return results
```

### Example responses

**LA City neighborhood (Beverly Grove):**
```json
{
  "neighborhood": "Beverly Grove",
  "city": "Los Angeles",
  "neighborhood_type": "segment-of-a-city",
  "neighborhood_city_slug": "los-angeles",
  "place_category": "la_city_neighborhood",
  "city_is_incorporated": true
}
```

**Standalone city (Pasadena):**
```json
{
  "neighborhood": "Pasadena",
  "city": "Pasadena",
  "neighborhood_type": "standalone-city",
  "neighborhood_city_slug": null,
  "place_category": "standalone_city",
  "city_is_incorporated": true
}
```

**Unincorporated area (Marina del Rey):**
```json
{
  "neighborhood": "Marina Del Rey",
  "city": "Unincorporated",
  "neighborhood_type": "unincorporated-area",
  "neighborhood_city_slug": null,
  "place_category": "unincorporated_area",
  "city_is_incorporated": false
}
```

### Frontend usage

```javascript
// Render appropriate label based on place_category
function renderPlaceLabel(result) {
  switch (result.place_category) {
    case 'la_city_neighborhood':
      return `${result.neighborhood} (City of LA)`;
    
    case 'standalone_city':
      return `${result.neighborhood}`;  // Just city name, no redundancy
    
    case 'unincorporated_area':
      return `${result.neighborhood} — Unincorporated LA County`;
    
    default:
      return result.neighborhood || 'Unknown';
  }
}
```

### Data sources

Fields come from:
- **`type`, `city`**: `la_neighborhoods_comprehensive.geojson` (LA Times Mapping LA)
- **`city_type`, `city_name`**: `la_county_cities.geojson` (LA County GIS)

### Testing

Test locations:
```bash
# LA City neighborhood
curl "https://api.stilesdata.com/la-geography/lookup?lat=34.0665&lon=-118.3718"
# → place_category: "la_city_neighborhood"

# Standalone city
curl "https://api.stilesdata.com/la-geography/lookup?lat=34.1478&lon=-118.1445"
# → place_category: "standalone_city"

# Unincorporated area
curl "https://api.stilesdata.com/la-geography/lookup?lat=33.9807&lon=-118.4517"
# → place_category: "unincorporated_area"
```

---

## Demographics (JSON instead of Parquet)

**Added**: 2025-11-30

### Problem

Lambda layers have a 50MB zipped size limit. Adding pandas + pyarrow for Parquet reading exceeded this limit.

### Solution

Convert demographics Parquet files to JSON (~49 KB total) and load with standard library. No pandas needed!

**Benefits:**
- No pandas dependency
- Smaller files (49 KB JSON vs 127 KB Parquet)
- Faster parsing
- Standard library only

**Process:**
```bash
uv run python scripts/convert_demographics_to_json.py
aws s3 cp data/standard/*_demographics.json s3://stilesdata.com/la-geography/
```

**Performance:**
- Cold start: +200ms (loading 49 KB JSON)
- Warm requests: Zero impact

---

## Response field evolution

| Version | Fields | Notes |
|---------|--------|-------|
| v1.0 | Basic lookups (neighborhood, city, etc.) | Initial release |
| v1.1 | + `region` | Added LA regions layer |
| v1.2 | + demographics | neighborhood_demographics, city_demographics |
| v1.3 | + governance | neighborhood_type, place_category, etc. |

All additions are backward compatible - new fields are added, existing fields unchanged.

