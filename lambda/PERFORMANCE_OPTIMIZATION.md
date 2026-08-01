# API performance optimization plan

**Current performance: ~12.6s response time (SLOW!)**

## Problem analysis

The API is loading ~35-40 MB of GeoJSON files on every cold start:

| Layer | Size | Features | Impact |
|-------|------|----------|--------|
| la_county_cities | 13.5 MB | 88 | 🔴 Huge |
| la_neighborhoods_comprehensive | 5.7 MB | 270 | 🔴 Large |
| lacofd_station_boundaries | 5.1 MB | 175 | 🔴 Large |
| la_county_school_districts | 4.3 MB | 85 | 🟡 Medium |
| la_city_neighborhood_councils | 2.8 MB | 99 | 🟡 Medium |
| la_county_election_precincts | ? MB | 1,502 | 🟡 Medium |
| Others (8 layers) | ~5 MB | Various | 🟢 Small |

**Total**: 35-40 MB loaded from S3, parsed, and converted to Shapely geometries on every cold start.

## Optimization strategies

### 1. Use simplified geometries ⚡ **Quick win**

We already have simplified neighborhoods (1.2 MB vs 5.7 MB). Create simplified versions of other large layers.

**Impact**: Reduce cold start by ~60-70%
**Effort**: Low (run simplify script for each layer)

```bash
# Create simplified versions
python scripts/simplify_neighborhoods.py --input data/standard/la_county_cities.geojson \
  --output data/standard/la_county_cities_simplified.geojson

# Expected reductions:
# - la_county_cities: 13.5 MB → ~3 MB (78% smaller)
# - lacofd_station_boundaries: 5.1 MB → ~1 MB (80% smaller)
# - school_districts: 4.3 MB → ~1 MB (77% smaller)
```

### 2. Add spatial indexing with STRtree 🚀 **High impact**

Point-in-polygon is slow when done sequentially. Use Shapely's STRtree for O(log n) lookups instead of O(n).

**Impact**: 10-50x faster queries (especially for layers with many features)
**Effort**: Medium

```python
from shapely.strtree import STRtree

def load_layers():
    for layer_config in LAYERS:
        # ... load features ...
        
        # Build spatial index
        geometries = [f['geometry'] for f in features]
        tree = STRtree(geometries)
        
        _layer_cache[layer_name] = {
            "features": features,
            "spatial_index": tree,  # NEW
            "config": layer_config
        }

def query_point(lat, lon):
    point = Point(lon, lat)
    
    for layer_name, layer_data in _layer_cache.items():
        tree = layer_data.get("spatial_index")
        features = layer_data["features"]
        
        # Use spatial index for fast lookup
        possible_matches_idx = tree.query(point, predicate='contains')
        matches = [features[i] for i in possible_matches_idx]
        # ... process matches ...
```

### 3. Keep Lambda warm with scheduled pings 🔥 **Easy**

Use EventBridge to ping the Lambda every 5 minutes to keep it warm.

**Impact**: Eliminate most cold starts
**Effort**: Low
**Cost**: ~$0.50/month

```yaml
# Add to template.yaml
WarmUpSchedule:
  Type: AWS::Events::Rule
  Properties:
    ScheduleExpression: rate(5 minutes)
    Targets:
      - Arn: !GetAtt LookupFunction.Arn
        Id: WarmUpTarget
        Input: '{"warmup": true}'

WarmUpPermission:
  Type: AWS::Lambda::Permission
  Properties:
    FunctionName: !Ref LookupFunction
    Action: lambda:InvokeFunction
    Principal: events.amazonaws.com
    SourceArn: !GetAtt WarmUpSchedule.Arn
```

### 4. Lazy load layers 📦 **Medium effort**

Only load frequently-used layers on cold start. Load others on-demand.

**Impact**: Reduce cold start by ~50%
**Effort**: Medium

```python
PRIORITY_LAYERS = [
    "la_neighborhoods_comprehensive",
    "la_county_cities",
    "la_regions",
    "lapd_divisions"
]

def load_layers(priority_only=True):
    layers_to_load = PRIORITY_LAYERS if priority_only else [l["name"] for l in LAYERS]
    # ... load only specified layers ...

# In lambda_handler:
if not _layer_cache:
    load_layers(priority_only=True)  # Fast initial load

# Later, lazy load others as needed
def ensure_layer_loaded(layer_name):
    if layer_name not in _layer_cache:
        load_single_layer(layer_name)
```

### 5. Use compressed format (GeoParquet) 💾 **Best long-term**

GeoParquet is 5-10x smaller and faster to load than GeoJSON.

**Impact**: 80-90% smaller files, 3-5x faster parsing
**Effort**: High (requires Parquet in Lambda layer)

```python
# Would require adding pyarrow/geopandas to Lambda layer
# But we removed those to keep layer small...
# Trade-off to consider
```

### 6. Pre-built spatial index 🗂️ **Advanced**

Store R-tree indexes alongside GeoJSON for instant lookups.

**Impact**: Near-instant queries
**Effort**: High

```python
import pickle

# Pre-build and save
tree = STRtree(geometries)
with open('neighborhoods_index.pkl', 'wb') as f:
    pickle.dump(tree, f)

# Load in Lambda
tree = pickle.load(...)  # Much faster than building from scratch
```

## Recommended approach

**Phase 1: Quick wins (1-2 hours)**
1. ✅ Create simplified versions of large layers
2. ✅ Update config to use simplified versions
3. ✅ Add STRtree spatial indexing
4. ✅ Deploy and test

**Expected result**: Cold start ~3-4s (down from 12.6s), warm requests ~200-300ms

**Phase 2: Keep warm (30 minutes)**
1. ✅ Add EventBridge schedule to ping every 5 minutes
2. ✅ Handle warmup events gracefully

**Expected result**: Most requests are warm (~200-300ms)

**Phase 3: Advanced (if needed)**
1. Consider lazy loading for rarely-used layers
2. Explore GeoParquet for even better compression

## File size targets

| Layer | Current | Simplified | Reduction |
|-------|---------|------------|-----------|
| neighborhoods | 5.7 MB | 1.2 MB | 79% ✅ Done |
| cities | 13.5 MB | ~3 MB | 78% |
| lacofd_boundaries | 5.1 MB | ~1 MB | 80% |
| school_districts | 4.3 MB | ~1 MB | 77% |
| **Total** | **~35 MB** | **~8 MB** | **77%** |

## Testing

```bash
# Test cold start
aws lambda update-function-configuration \
  --function-name la-geography-lookup-api-LookupFunction-* \
  --environment Variables={FORCE_COLD_START=true}

# Measure
time curl "https://api.stilesdata.com/la-geography/lookup?lat=34.05&lon=-118.24"

# Test warm
for i in {1..5}; do
  time curl "https://api.stilesdata.com/la-geography/lookup?lat=34.05&lon=-118.24"
done
```

## Cost analysis

Current: ~$0.30/month (minimal traffic)

With optimizations:
- Simplified files: No change (same request count)
- Warm pings: +$0.50/month (720 pings/day × $0.20/million)
- **Total**: ~$0.80/month

Still extremely cheap!

