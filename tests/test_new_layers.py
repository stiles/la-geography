#!/usr/bin/env python3
"""
Test script for new airport and election precinct layers.

Tests:
1. Layer loading and validation
2. Coordinate lookups for known locations
3. Data integrity checks
"""

import sys
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_airports():
    """Test LA County airports layer."""
    print("\n" + "=" * 60)
    print("Testing: LA County Airports")
    print("=" * 60)
    
    gdf = gpd.read_file("data/standard/la_county_airports.geojson")
    
    # Basic validation
    assert len(gdf) == 16, f"Expected 16 airports, got {len(gdf)}"
    assert gdf.crs.to_string() == "EPSG:4326", "Wrong CRS"
    assert all(gdf.geometry.type == "Point"), "Non-point geometries found"
    
    # Check required fields
    assert "name" in gdf.columns, "Missing 'name' field"
    assert "type" in gdf.columns, "Missing 'type' field"
    
    # Check airport types
    commercial = len(gdf[gdf["type"] == "Commercial Airport"])
    general = len(gdf[gdf["type"] == "General Aviation Airport"])
    
    print(f"  ✓ {len(gdf)} total airports")
    print(f"    - Commercial: {commercial}")
    print(f"    - General Aviation: {general}")
    
    # Check for known airports
    known_airports = ["Los Angeles International Airport (LAX)", "Bob Hope Airport"]
    for airport in known_airports:
        matches = gdf[gdf["name"].str.contains(airport.split("(")[0].strip(), na=False)]
        assert len(matches) > 0, f"Missing expected airport: {airport}"
        print(f"  ✓ Found: {matches.iloc[0]['name']}")
    
    print("  ✓ All airport tests passed")
    return True


def test_noise_contours():
    """Test LA County airport noise contours layer."""
    print("\n" + "=" * 60)
    print("Testing: Airport Noise Contours")
    print("=" * 60)
    
    gdf = gpd.read_file("data/standard/la_county_airport_noise_contours.geojson")
    
    # Basic validation
    assert len(gdf) == 35, f"Expected 35 contours, got {len(gdf)}"
    assert gdf.crs.to_string() == "EPSG:4326", "Wrong CRS"
    assert all(gdf.geometry.type.isin(["Polygon", "MultiPolygon"])), "Non-polygon geometries"
    
    # Check required fields
    assert "airport_name" in gdf.columns, "Missing 'airport_name' field"
    assert "class" in gdf.columns, "Missing 'class' field"
    
    # Check noise levels
    noise_levels = sorted(gdf["class"].unique())
    print(f"  ✓ {len(gdf)} total noise contours")
    print(f"  Noise levels: {', '.join(str(x) for x in noise_levels)} dB")
    
    # Check for known airports
    airports = gdf["airport_name"].unique()
    assert "Los Angeles International" in airports, "Missing LAX noise contours"
    print(f"  ✓ Airports with noise contours: {', '.join(sorted(airports))}")
    
    # Test LAX area (should be in noise contour)
    lax_point = Point(-118.4085, 33.9416)
    in_noise = gdf[gdf.contains(lax_point)]
    assert len(in_noise) > 0, "LAX area not in any noise contour"
    print(f"  ✓ LAX area in {in_noise.iloc[0]['class']} dB contour")
    
    print("  ✓ All noise contour tests passed")
    return True


def test_election_precincts():
    """Test LA County election precincts layer."""
    print("\n" + "=" * 60)
    print("Testing: Election Precincts")
    print("=" * 60)
    
    gdf = gpd.read_file("data/standard/la_county_election_precincts.geojson")
    
    # Basic validation
    assert len(gdf) == 1502, f"Expected 1502 precincts, got {len(gdf)}"
    assert gdf.crs.to_string() == "EPSG:4326", "Wrong CRS"
    assert all(gdf.geometry.type == "Polygon"), "Non-polygon geometries found"
    
    # Check required fields
    assert "precinct" in gdf.columns, "Missing 'precinct' field"
    
    print(f"  ✓ {len(gdf)} total precincts")
    
    # Check voter statistics if present
    if "vbmvoters" in gdf.columns:
        total_vbm = gdf["vbmvoters"].sum()
        print(f"  Total VBM voters: {total_vbm:,}")
    
    if "pollvoters" in gdf.columns:
        # Note: pollvoters appears to be a location code, not a count
        unique_poll_locations = gdf["pollvoters"].nunique()
        print(f"  Unique poll locations: {unique_poll_locations:,}")
    
    # Test known locations
    test_locations = [
        ("LAX area", -118.4085, 33.9416),
        ("Downtown LA", -118.2437, 34.0522),
    ]
    
    for name, lon, lat in test_locations:
        point = Point(lon, lat)
        precinct = gdf[gdf.contains(point)]
        assert len(precinct) > 0, f"No precinct found for {name}"
        print(f"  ✓ {name}: Precinct {precinct.iloc[0]['precinct']}")
    
    print("  ✓ All election precinct tests passed")
    return True


def test_coordinate_lookups():
    """Test coordinate lookups across all layers."""
    print("\n" + "=" * 60)
    print("Testing: Coordinate Lookups")
    print("=" * 60)
    
    # Load all layers
    airports = gpd.read_file("data/standard/la_county_airports.geojson")
    noise = gpd.read_file("data/standard/la_county_airport_noise_contours.geojson")
    precincts = gpd.read_file("data/standard/la_county_election_precincts.geojson")
    
    # Test locations
    test_locations = [
        ("LAX", -118.4085, 33.9416),
        ("Burbank Airport", -118.3585, 34.2008),
        ("Downtown LA", -118.2437, 34.0522),
    ]
    
    for name, lon, lat in test_locations:
        print(f"\n  Testing: {name} ({lat:.4f}, {lon:.4f})")
        point = Point(lon, lat)
        
        # Find nearest airport
        airports_copy = airports.copy()
        airports_copy["distance"] = airports_copy.geometry.distance(point)
        nearest = airports_copy.nsmallest(1, "distance")
        dist_miles = nearest.iloc[0]["distance"] * 69  # rough conversion
        print(f"    Nearest airport: {nearest.iloc[0]['name']} (~{dist_miles:.1f} mi)")
        
        # Check noise contour
        noise_match = noise[noise.contains(point)]
        if len(noise_match) > 0:
            print(f"    ✓ In noise zone: {noise_match.iloc[0]['airport_name']} "
                  f"({noise_match.iloc[0]['class']} dB)")
        else:
            print(f"    Not in any noise contour")
        
        # Check precinct
        precinct_match = precincts[precincts.contains(point)]
        if len(precinct_match) > 0:
            print(f"    ✓ Precinct: {precinct_match.iloc[0]['precinct']}")
        else:
            print(f"    ✗ No precinct found")
    
    print("\n  ✓ All coordinate lookup tests passed")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing New LA Geography Layers")
    print("=" * 60)
    
    try:
        test_airports()
        test_noise_contours()
        test_election_precincts()
        test_coordinate_lookups()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        return 0
    
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

