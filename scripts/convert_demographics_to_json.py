#!/usr/bin/env python3
"""
Convert demographics Parquet files to JSON for Lambda consumption.

This allows the Lambda handler to read demographics without needing pandas,
keeping the layer size small.
"""

import json
from pathlib import Path
import pandas as pd

# Layers with demographics to convert
LAYERS = [
    {
        "name": "la_neighborhoods_comprehensive",
        "id_field": "slug",
    },
    {
        "name": "la_county_cities",
        "id_field": "city_name",
    },
    {
        "name": "la_regions",
        "id_field": "slug",
    },
]

DATA_DIR = Path("data/standard")
OUTPUT_DIR = DATA_DIR


def convert_to_json(layer_name: str, id_field: str):
    """Convert a demographics Parquet file to JSON."""
    
    parquet_file = DATA_DIR / f"{layer_name}_demographics.parquet"
    json_file = OUTPUT_DIR / f"{layer_name}_demographics.json"
    
    if not parquet_file.exists():
        print(f"⚠️  Skipping {layer_name} (file not found)")
        return
    
    print(f"Converting {layer_name}...")
    
    # Read Parquet
    df = pd.read_parquet(parquet_file)
    
    # Create dictionary keyed by ID field
    demographics_dict = {}
    
    for _, row in df.iterrows():
        feature_id = row[id_field]
        
        # Convert to simple dict with only the fields we need
        demo_data = {
            "population": int(row.get("pop_total", 0)),
            "pop_hispanic": int(row.get("pop_hispanic", 0)),
            "pop_white_nh": int(row.get("pop_white_nh", 0)),
            "pop_black_nh": int(row.get("pop_black_nh", 0)),
            "pop_asian_nh": int(row.get("pop_asian_nh", 0)),
            "pop_other_nh": int(row.get("pop_aian_nh", 0) + 
                                row.get("pop_nhpi_nh", 0) + 
                                row.get("pop_other_nh", 0) + 
                                row.get("pop_two_or_more_nh", 0)),
        }
        
        demographics_dict[feature_id] = demo_data
    
    # Write JSON
    with open(json_file, 'w') as f:
        json.dump(demographics_dict, f, separators=(',', ':'))
    
    # Report sizes
    parquet_size = parquet_file.stat().st_size / 1024
    json_size = json_file.stat().st_size / 1024
    
    print(f"  ✅ {json_file.name}")
    print(f"     {len(demographics_dict)} features")
    print(f"     {parquet_size:.1f} KB (Parquet) → {json_size:.1f} KB (JSON)")


def main():
    print("Converting demographics Parquet files to JSON...\n")
    
    for layer in LAYERS:
        convert_to_json(layer["name"], layer["id_field"])
        print()
    
    print("✅ Conversion complete!")
    print("\nNext steps:")
    print("  1. Upload JSON files to S3: make s3-upload")
    print("  2. Deploy updated Lambda: cd lambda && sam deploy")


if __name__ == "__main__":
    main()

