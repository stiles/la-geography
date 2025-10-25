# Testing Census Demographics Pipeline

Step-by-step guide for testing the Census demographics enrichment pipeline.

## Prerequisites

1. **Install dependencies:**
   ```bash
   uv pip install -r requirements.txt
   ```
   
   New dependencies for Census:
   - `pygris>=0.1.6` - Downloads Census TIGER/Line shapefiles
   - `census>=0.8.22` - Census API client

2. **Get Census API key:**
   Follow instructions in [CENSUS_SETUP.md](CENSUS_SETUP.md)

3. **Have boundary data:**
   ```bash
   # If you don't have boundaries yet
   make fetch
   
   # Process them
   python scripts/process_raw.py
   ```

## Quick Test (Recommended)

Test with LAPD bureaus (only 4 features, runs in ~2-3 minutes):

```bash
# 1. Fetch Census data (~2 minutes, ~254K blocks)
make fetch-census

# 2. Apportion to LAPD bureaus (~30 seconds)
make apportion-census-test

# 3. Validate results
python scripts/validate_apportionment.py --layer lapd_bureaus
```

**Expected output structure:**
```
data/census/
├── raw/
│   ├── blocks_2020_geometries.geojson     (~500 MB)
│   └── blocks_2020_demographics.parquet   (~50 MB)
└── processed/
    └── blocks_2020_enriched.parquet       (~400 MB)

data/standard/
└── lapd_bureaus_demographics.parquet      (~5 KB)
```

**Expected population totals (LAPD bureaus):**
- Central Bureau: ~1.2M
- South Bureau: ~1.0M
- Valley Bureau: ~1.5M
- West Bureau: ~1.1M
- **Total: ~4.8M** (covers most of LA City's ~3.9M population)

Note: LAPD service area extends slightly beyond city limits.

## Full Test (All Layers)

Run for all 13 polygon layers (~5-10 minutes):

```bash
# Apportion to all polygon layers
make apportion-census

# Validate all results
make validate-census
```

## Individual Layer Test

Test a specific layer:

```bash
# Apportion
python scripts/apportion_census.py --layer la_city_neighborhoods

# Validate
python scripts/validate_apportionment.py --layer la_city_neighborhoods
```

## Validation Checks

The validation script checks:

### 1. Conservation of Totals
Population should be conserved within 1% (accounting for boundary slivers):
```
Variable              Source      Apportioned    Diff %
pop_total         10,014,009       10,005,123     0.09%  ✓
```

### 2. Benchmark Checks
Known 2020 Census totals:
- LA County: 10,014,009 people
- LA City: 3,898,747 people

### 3. Data Quality
- No negative values
- No null values
- All target features have data

## Expected Performance

Timing estimates (on typical laptop):

| Step | Time | Output Size |
|------|------|-------------|
| Fetch Census blocks | 2-3 min | ~500 MB |
| Apportion to 4 features (bureaus) | 30 sec | ~5 KB |
| Apportion to 21 features (divisions) | 1 min | ~20 KB |
| Apportion to 1,191 features (RDs) | 3-5 min | ~500 KB |
| Apportion to all 13 layers | 5-10 min | ~2 MB total |

## Troubleshooting

### "Census blocks not found"
Run `make fetch-census` first.

### "Layer not found"
Make sure you've run `python scripts/process_raw.py` to create standardized layers.

### Population totals don't match
- Check tolerance setting (default 1%)
- Some features extend beyond Census coverage (e.g., water bodies, airports)
- Boundary updates since 2020 may cause discrepancies

### Slow performance
- Filter to smaller areas first (e.g., test with bureaus before reporting districts)
- Check available memory (Census blocks are ~400 MB in memory)
- Use bbox filtering (automatic in apportion script)

### Census API errors
- Check API key is valid
- Verify network connection
- API may have rate limits (500/day without key)
- Try again later if Census servers are busy

## Sample Output Files

### Demographics Parquet
```python
import pandas as pd
df = pd.read_parquet('data/standard/lapd_bureaus_demographics.parquet')
print(df.columns)

# Output:
# ['bureau', 'pop_total', 'pop_hispanic', 'pop_white_nh', 'pop_black_nh',
#  'pop_asian_nh', 'housing_total', 'housing_occupied', 'housing_vacant',
#  'source_blocks_count', 'apportioned_at', 'census_vintage', 'source_layer']
```

### Joined with Boundaries
```python
import geopandas as gpd
boundaries = gpd.read_file('data/standard/lapd_bureaus.geojson')
demographics = pd.read_parquet('data/standard/lapd_bureaus_demographics.parquet')
joined = boundaries.merge(demographics, on='bureau')

# Now you can map it
joined.plot(column='pop_total', legend=True, figsize=(10, 10))
```

## Next Steps After Successful Test

1. **Upload to S3** (if using cloud storage):
   ```bash
   python scripts/s3_sync.py upload --layer lapd_bureaus_demographics
   ```

2. **Create visualizations**:
   ```python
   # Example: Hispanic percentage by division
   joined['pct_hispanic'] = joined['pop_hispanic'] / joined['pop_total'] * 100
   joined.plot(column='pct_hispanic', cmap='RdYlBu_r', legend=True)
   ```

3. **Generate summary reports**:
   ```python
   # Example: Top 5 divisions by population
   top5 = joined.nlargest(5, 'pop_total')[['division', 'pop_total']]
   print(top5)
   ```

## Clean Up (Optional)

To remove Census data and free disk space:

```bash
# Remove Census cache (~500 MB)
rm -rf data/census/

# Census blocks are also cached by pygris:
# Mac: ~/Library/Caches/pygris
# Linux: ~/.cache/pygris
```

## Support

For issues specific to Census data collection:
- See [CENSUS_SETUP.md](docs/CENSUS_SETUP.md)
- See [CENSUS_FIELDS.md](docs/CENSUS_FIELDS.md)

For issues with the pipeline scripts:
- Check script output for error messages
- Verify input files exist
- Run with `--help` flag for usage information

