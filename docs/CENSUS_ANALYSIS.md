# Census demographics analysis examples

Quick guide to exploring and analyzing Census demographics data.

## Quick statistics (`census_stats.py`)

Fast way to see demographics for any layer.

### Basic usage

```bash
# Show summary for a layer
python scripts/census_stats.py lapd_divisions
```

**Output:**
```
======================================================================
Demographics: lapd_divisions
======================================================================

Features: 21
Total population: 4,830,123
Total housing units: 1,812,456
Occupancy rate: 94.2%

Race/Ethnicity:
  Hispanic/Latino: 48.6%
  White (non-Hispanic): 28.4%
  Black (non-Hispanic): 8.9%
  Asian (non-Hispanic): 11.2%

Top 3 by population:
  77th Street                    368,245
  Southwest                      341,892
  Northeast                      325,678

Bottom 3 by population:
  Hollywood                      142,567
  Wilshire                       138,234
  Pacific                        127,891

Most diverse 3:
  Hollywood                        0.734
  Wilshire                         0.729
  Central                          0.721
```

### Show more features

```bash
# Top 10 by population
python scripts/census_stats.py la_city_neighborhoods --top 10
```

### Available layers

Run without arguments to see available layers:
```bash
python scripts/census_stats.py
```

## Comprehensive analysis (`analyze_demographics.py`)

In-depth analysis with superlatives, comparisons, and report generation.

### Analyze single layer

```bash
python scripts/analyze_demographics.py --layer lapd_bureaus
```

**Shows:**
- Total population and housing
- Demographic breakdown by race/ethnicity
- Superlatives (most populous, most diverse, highest density)
- Housing occupancy rates

### Analyze all layers

```bash
python scripts/analyze_demographics.py
```

Analyzes all 13 polygon layers with demographics and shows:
- Individual layer statistics
- Cross-layer comparisons
- Grand totals (with caveat about overlapping layers)

### Compare layers

```bash
python scripts/analyze_demographics.py --compare
```

Shows side-by-side comparison of:
- LA City vs LA County
- LAPD Bureaus
- Other major jurisdictions

### Generate report

```bash
python scripts/analyze_demographics.py --save-report
```

Creates `data/docs/DEMOGRAPHICS_REPORT.md` with:
- Summary table of all layers
- Key findings (population totals, percentages)
- Markdown format for easy sharing

**Example report snippet:**
```markdown
| Layer | Features | Population | % Hispanic | Housing Units |
|-------|----------|------------|------------|---------------|
| lapd_bureaus | 4 | 4,830,123 | 48.6% | 1,812,456 |
| lapd_divisions | 21 | 4,830,123 | 48.6% | 1,812,456 |
| la_city_boundary | 1 | 3,983,434 | 46.8% | 1,531,189 |
```

## Example insights

### Find most diverse neighborhoods

```bash
python scripts/census_stats.py la_city_neighborhoods --top 20
```

Look at the "Most diverse" section to see which neighborhoods have the most racial/ethnic diversity.

### Population density hotspots

```bash
python scripts/analyze_demographics.py --layer lapd_divisions
```

Check the "Highest density" superlative to see which division has the most people per square mile.

### Hispanic/Latino concentration

Both scripts show Hispanic/Latino percentages. Use `census_stats.py` for quick checks or `analyze_demographics.py` for comprehensive view with "Highest % Hispanic" superlative.

### Housing occupancy patterns

```bash
python scripts/census_stats.py la_city_parks
```

See occupancy rates to understand housing utilization patterns.

## Diversity index

Both scripts calculate a diversity index using:

```
diversity = 1 - (pct_hispanic² + pct_white_nh² + pct_black_nh² + pct_asian_nh²)
```

**Interpretation:**
- **0.0** = No diversity (100% one group)
- **0.75** = High diversity (well-mixed population)
- **Higher is more diverse**

This simplified index considers the four major race/ethnicity groups.

## Tips

1. **Start with quick stats** (`census_stats.py`) to explore
2. **Use comprehensive analysis** (`analyze_demographics.py`) for reports
3. **Generate reports** for sharing findings with others
4. **Combine with boundaries** for mapping (see main README)

## Custom analysis

Both scripts serve as examples. You can:
- Copy and modify for custom metrics
- Add your own superlatives
- Calculate additional derived fields
- Join with other datasets

**Example custom analysis:**
```python
import pandas as pd
import geopandas as gpd

# Load data
boundaries = gpd.read_file('data/standard/lapd_divisions.geojson')
demographics = pd.read_parquet('data/standard/lapd_divisions_demographics.parquet')

# Join
data = boundaries.merge(demographics, on='prec')

# Calculate child population (using external ACS data)
# Calculate income disparity
# Map patterns
# etc.
```

## Validation

These scripts also serve as validation tools:
- Check population totals are reasonable
- Verify percentages sum correctly
- Identify outliers or anomalies
- Compare against known benchmarks

If you see unexpected values, check:
1. Layer boundary correctness
2. Apportionment validation results
3. Census data source issues

## Performance

Both scripts are fast:
- `census_stats.py`: < 1 second per layer
- `analyze_demographics.py`: 5-10 seconds for all layers

Demographics files are small (< 50 KB each), so loading is quick.

---

**See also:**
- [CENSUS_FIELDS.md](CENSUS_FIELDS.md) - Variable definitions
- [CENSUS_TESTING.md](CENSUS_TESTING.md) - Validation procedures
- Main [README.md](../README.md) - Usage examples with mapping

