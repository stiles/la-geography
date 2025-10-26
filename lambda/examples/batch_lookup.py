#!/usr/bin/env python3
"""
Example: Batch lookup for multiple coordinates.

Loads coordinates from a CSV file and queries the API for each one.

Usage:
    python batch_lookup.py <api_url> <input_csv> <output_csv>
    
Input CSV format (with header):
    id,lat,lon,name
    1,34.0522,-118.2437,"Downtown LA"
    2,33.9850,-118.4695,"Venice Beach"
    
Output CSV includes all results fields.
"""

import sys
import csv
import time
import requests
from typing import List, Dict, Any


def lookup_location(api_url: str, lat: float, lon: float) -> Dict[str, Any]:
    """Query the API for a coordinate."""
    response = requests.get(api_url, params={"lat": lat, "lon": lon})
    response.raise_for_status()
    return response.json()


def batch_lookup(
    api_url: str,
    input_csv: str,
    output_csv: str,
    delay: float = 0.1
) -> None:
    """
    Perform batch lookup for coordinates in a CSV file.
    
    Args:
        api_url: API endpoint URL
        input_csv: Input CSV file with id,lat,lon,name columns
        output_csv: Output CSV file path
        delay: Delay between requests in seconds (for rate limiting)
    """
    # Read input CSV
    with open(input_csv, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Processing {len(rows)} locations...")
    
    # Process each row
    results = []
    for i, row in enumerate(rows, 1):
        row_id = row.get('id', i)
        lat = float(row['lat'])
        lon = float(row['lon'])
        name = row.get('name', f"Location {i}")
        
        print(f"{i}/{len(rows)}: {name} ({lat}, {lon})", end=" ... ")
        
        try:
            data = lookup_location(api_url, lat, lon)
            
            if data['status'] == 'success':
                result = {
                    'id': row_id,
                    'name': name,
                    'lat': lat,
                    'lon': lon,
                    **data['results']  # Unpack all result fields
                }
                results.append(result)
                print("✓")
            else:
                print(f"✗ Error: {data.get('message', 'Unknown')}")
                results.append({
                    'id': row_id,
                    'name': name,
                    'lat': lat,
                    'lon': lon,
                    'error': data.get('message', 'Unknown error')
                })
                
        except Exception as e:
            print(f"✗ Failed: {e}")
            results.append({
                'id': row_id,
                'name': name,
                'lat': lat,
                'lon': lon,
                'error': str(e)
            })
        
        # Rate limiting
        if i < len(rows):
            time.sleep(delay)
    
    # Write output CSV
    if results:
        fieldnames = list(results[0].keys())
        
        with open(output_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        print(f"\n✅ Results written to {output_csv}")
    else:
        print("\n❌ No results to write")


def main():
    """Run batch lookup."""
    if len(sys.argv) != 4:
        print("Usage: python batch_lookup.py <api_url> <input_csv> <output_csv>")
        print("\nExample:")
        print("  python batch_lookup.py \\")
        print("    https://abc123.execute-api.us-west-2.amazonaws.com/prod/lookup \\")
        print("    locations.csv \\")
        print("    results.csv")
        sys.exit(1)
    
    api_url = sys.argv[1]
    input_csv = sys.argv[2]
    output_csv = sys.argv[3]
    
    batch_lookup(api_url, input_csv, output_csv)


if __name__ == "__main__":
    main()

