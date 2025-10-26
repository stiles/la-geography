# API usage examples

Example scripts demonstrating how to use the LA Geography point-lookup API.

## test_api.py

Test the API with several known LA locations.

```bash
python test_api.py https://YOUR-API-ID.execute-api.us-west-2.amazonaws.com/prod/lookup
```

**Output:**
```
Testing API: https://...
======================================================================

🔍 Testing: Downtown LA (City Hall)

Location: (34.0537, -118.2427)
==================================================
Neighborhood             : Downtown
City                     : Los Angeles
LAPD Division            : Central
LAPD Bureau              : Central Bureau
LAFD Station             : Station 3
...
```

## batch_lookup.py

Process multiple coordinates from a CSV file.

**Input CSV format** (`sample_locations.csv`):
```csv
id,lat,lon,name
1,34.0522,-118.2437,"Downtown LA"
2,33.9850,-118.4695,"Venice Beach"
```

**Usage:**
```bash
python batch_lookup.py \
  https://YOUR-API-ID.execute-api.us-west-2.amazonaws.com/prod/lookup \
  sample_locations.csv \
  results.csv
```

**Output CSV** includes all result fields:
```csv
id,name,lat,lon,neighborhood,city,lapd_division,lapd_bureau,...
1,Downtown LA,34.0522,-118.2437,Downtown,Los Angeles,Central,Central Bureau,...
2,Venice Beach,33.9850,-118.4695,Venice,Los Angeles,Pacific,West Bureau,...
```

## Requirements

Install required dependencies:

```bash
pip install requests
```

Or use from the project root:

```bash
pip install -r requirements.txt
```

