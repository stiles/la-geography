#!/usr/bin/env python3
"""
Example script to test the LA Geography point-lookup API.

Usage:
    python test_api.py <api_url>
    
Example:
    python test_api.py https://abc123.execute-api.us-west-2.amazonaws.com/prod/lookup
"""

import sys
import requests
from typing import Dict, Any


def lookup_location(api_url: str, lat: float, lon: float) -> Dict[str, Any]:
    """
    Query the point-lookup API for a coordinate.
    
    Args:
        api_url: Base API endpoint URL
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        
    Returns:
        API response as dict
    """
    response = requests.get(api_url, params={"lat": lat, "lon": lon})
    response.raise_for_status()
    return response.json()


def format_results(data: Dict[str, Any]) -> str:
    """Format API results for display."""
    query = data["query"]
    results = data["results"]
    
    lines = [
        f"\nLocation: ({query['lat']}, {query['lon']})",
        "=" * 50,
    ]
    
    # Order results for display
    display_order = [
        ("neighborhood", "Neighborhood"),
        ("city", "City"),
        ("lapd_division", "LAPD Division"),
        ("lapd_bureau", "LAPD Bureau"),
        ("lafd_station", "LAFD Station"),
        ("lacofd_station", "LA County Fire Station"),
        ("council_district", "Council District"),
        ("neighborhood_council", "Neighborhood Council"),
        ("school_district", "School District"),
    ]
    
    for key, label in display_order:
        value = results.get(key)
        if value:
            lines.append(f"{label:25s}: {value}")
        else:
            lines.append(f"{label:25s}: (not in coverage area)")
    
    return "\n".join(lines)


def main():
    """Test the API with several known LA locations."""
    if len(sys.argv) < 2:
        print("Usage: python test_api.py <api_url>")
        print("\nExample:")
        print("  python test_api.py https://abc123.execute-api.us-west-2.amazonaws.com/prod/lookup")
        sys.exit(1)
    
    api_url = sys.argv[1]
    
    # Test locations
    test_locations = [
        {
            "name": "Downtown LA (City Hall)",
            "lat": 34.0537,
            "lon": -118.2427,
        },
        {
            "name": "Venice Beach",
            "lat": 33.9850,
            "lon": -118.4695,
        },
        {
            "name": "Pasadena (City Hall)",
            "lat": 34.1478,
            "lon": -118.1445,
        },
        {
            "name": "Santa Monica (Pier)",
            "lat": 34.0095,
            "lon": -118.4974,
        },
        {
            "name": "Hollywood (Walk of Fame)",
            "lat": 34.1016,
            "lon": -118.3267,
        },
    ]
    
    print(f"\nTesting API: {api_url}")
    print("=" * 70)
    
    for location in test_locations:
        print(f"\n🔍 Testing: {location['name']}")
        
        try:
            data = lookup_location(api_url, location["lat"], location["lon"])
            
            if data["status"] == "success":
                print(format_results(data))
            else:
                print(f"❌ Error: {data.get('message', 'Unknown error')}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        except KeyError as e:
            print(f"❌ Unexpected response format: {e}")
    
    print("\n" + "=" * 70)
    print("✅ Testing complete!\n")


if __name__ == "__main__":
    main()

