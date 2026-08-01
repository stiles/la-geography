# Simplified neighborhoods GeoJSON

A lightweight version of the comprehensive neighborhoods layer optimized for web mapping.

## Files

| File | Size | Coordinates | Use case |
|------|------|-------------|----------|
| `la_neighborhoods_comprehensive.geojson` | 5.7 MB | 139,395 | Detailed analysis, high-quality maps |
| `la_neighborhoods_comprehensive_simplified.geojson` | 1.2 MB | 27,954 | Web mapping, quick loading |

**Size reduction: 79.4%**

## URLs

- **Full version**: https://stilesdata.com/la-geography/la_neighborhoods_comprehensive.geojson
- **Simplified version**: https://stilesdata.com/la-geography/la_neighborhoods_comprehensive_simplified.geojson

## What's different

### Simplified geometries
- Tolerance: 0.0001 degrees (~10-15 meters at LA's latitude)
- Douglas-Peucker algorithm preserves topology
- Visual difference is imperceptible at typical web map zoom levels

### Essential properties only
The simplified version includes only:
- `name` - Display name (e.g., "Beverly Grove")
- `slug` - URL-safe identifier (e.g., "beverly-grove")
- `region` - Geographic region (e.g., "central-la")
- `type` - Feature type (e.g., "segment-of-a-city", "city")
- `city` - Parent city if LA City neighborhood (e.g., "los-angeles")

Removed fields (available in full version):
- `county` - Always "los-angeles"
- `area_sqmi` - Area in square miles
- `source_url` - Source data URL
- `fetched_at` - Timestamp

## Usage

### Leaflet example

```javascript
// Load simplified version for faster initial load
fetch('https://stilesdata.com/la-geography/la_neighborhoods_comprehensive_simplified.geojson')
  .then(response => response.json())
  .then(data => {
    L.geoJSON(data, {
      style: {
        color: '#333',
        weight: 1,
        fillOpacity: 0.1
      },
      onEachFeature: (feature, layer) => {
        layer.bindPopup(`
          <strong>${feature.properties.name}</strong><br>
          ${feature.properties.region}
        `);
      }
    }).addTo(map);
  });
```

### Mapbox GL JS example

```javascript
map.addSource('neighborhoods', {
  type: 'geojson',
  data: 'https://stilesdata.com/la-geography/la_neighborhoods_comprehensive_simplified.geojson'
});

map.addLayer({
  id: 'neighborhoods-fill',
  type: 'fill',
  source: 'neighborhoods',
  paint: {
    'fill-color': '#0080ff',
    'fill-opacity': 0.1
  }
});

map.addLayer({
  id: 'neighborhoods-line',
  type: 'line',
  source: 'neighborhoods',
  paint: {
    'line-color': '#333',
    'line-width': 1
  }
});
```

## When to use each version

### Use simplified (1.2 MB) for:
- ✅ Web maps and interactive visualizations
- ✅ Mobile applications
- ✅ Quick prototypes
- ✅ Overlays on base maps (zoom levels 8-15)

### Use full (5.7 MB) for:
- ✅ High-resolution print maps
- ✅ Detailed spatial analysis
- ✅ Close-up views (zoom > 16)
- ✅ When you need all metadata fields
- ✅ Precise area calculations

## Regenerating

The simplified version is generated from the full version using the Douglas-Peucker algorithm.

```bash
# Regenerate simplified version
make simplify

# Or run directly
python scripts/simplify_neighborhoods.py

# Upload to S3
aws s3 cp data/standard/la_neighborhoods_comprehensive_simplified.geojson \
  s3://stilesdata.com/la-geography/ --profile haekeo
```

## Performance comparison

Loading times over 4G connection (~10 Mbps):

| Version | File size | Load time | Parse time | Total |
|---------|-----------|-----------|------------|-------|
| Full | 5.7 MB | ~4.5s | ~400ms | ~5s |
| Simplified | 1.2 MB | ~1.0s | ~150ms | ~1.2s |

**Improvement: 76% faster loading**

## Visual quality

The simplification is designed to be visually imperceptible at typical web map zoom levels (8-15). At very high zoom levels (16+), you may notice slight differences in boundary precision.

For "Where's my LA", the simplified version is perfect for:
- Neighborhood overlay on the map
- Neighborhood selection/highlighting
- Tooltips and popups

## LA County demographics

For quick reference, here are the county-wide demographics to compare against neighborhoods:

```javascript
const LA_COUNTY_DEMOGRAPHICS = {
  population: 10014009,
  pop_hispanic: 4804763,     // 48.0%
  pop_white_nh: 2563609,     // 25.6%
  pop_black_nh: 760689,      // 7.6%
  pop_asian_nh: 1474237,     // 14.7%
  pop_other_nh: 410711       // 4.1%
};
```

## Source

Simplified from [LA Times Mapping LA comprehensive neighborhoods](https://github.com/datadesk/boundaries.latimes.com) using `scripts/simplify_neighborhoods.py`.

