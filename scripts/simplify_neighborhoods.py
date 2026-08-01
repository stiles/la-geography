#!/usr/bin/env python3
"""
Create a simplified version of the comprehensive neighborhoods GeoJSON.

The full version has detailed geometries (~6MB) which is too large for
quick web mapping. This creates a simplified version with:
1. Simplified geometries (tolerance ~10m, reduces size ~60-70%)
2. Essential properties only (name, slug, region, type)

Usage:
    python scripts/simplify_neighborhoods.py
    
Output:
    data/standard/la_neighborhoods_comprehensive_simplified.geojson
"""

from pathlib import Path
import geopandas as gpd
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from geo_utils import ensure_wgs84


def simplify_neighborhoods(
    input_path: Path,
    output_path: Path,
    tolerance: float = 0.0001  # ~10-15m in degrees at LA's latitude
) -> None:
    """
    Simplify neighborhood geometries and properties.
    
    Args:
        input_path: Path to full neighborhoods GeoJSON
        output_path: Path for simplified output
        tolerance: Simplification tolerance in degrees (default ~10-15m)
    """
    print(f"\n{'='*70}")
    print("Creating Simplified Neighborhoods GeoJSON")
    print(f"{'='*70}")
    
    # Read full data
    print(f"\nReading {input_path.name}...")
    gdf = gpd.read_file(input_path)
    
    # Get initial size
    initial_size = input_path.stat().st_size / (1024 * 1024)
    
    def count_coords(geom):
        """Count coordinates in any geometry type."""
        if geom.geom_type == 'Polygon':
            return sum(len(list(ring.coords)) for ring in ([geom.exterior] + list(geom.interiors)))
        elif geom.geom_type == 'MultiPolygon':
            return sum(count_coords(poly) for poly in geom.geoms)
        elif geom.geom_type == 'LineString':
            return len(list(geom.coords))
        else:
            return 0
    
    initial_coords = sum(count_coords(geom) for geom in gdf.geometry)
    
    print(f"  Features: {len(gdf)}")
    print(f"  File size: {initial_size:.2f} MB")
    print(f"  Total coordinates: {initial_coords:,}")
    
    # Simplify geometries
    print(f"\nSimplifying geometries (tolerance: {tolerance} degrees)...")
    gdf_simplified = gdf.copy()
    gdf_simplified.geometry = gdf.geometry.simplify(tolerance, preserve_topology=True)
    
    # Ensure WGS84
    gdf_simplified = ensure_wgs84(gdf_simplified)
    
    # Save simplified version
    print(f"\nSaving to {output_path.name}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf_simplified.to_file(output_path, driver="GeoJSON")
    
    # Report results
    final_size = output_path.stat().st_size / (1024 * 1024)
    final_coords = sum(count_coords(geom) for geom in gdf_simplified.geometry)
    
    size_reduction = ((initial_size - final_size) / initial_size) * 100
    coord_reduction = ((initial_coords - final_coords) / initial_coords) * 100
    
    print(f"\n{'='*70}")
    print("Results:")
    print(f"{'='*70}")
    print(f"  Original size:     {initial_size:.2f} MB")
    print(f"  Simplified size:   {final_size:.2f} MB")
    print(f"  Size reduction:    {size_reduction:.1f}%")
    print(f"")
    print(f"  Original coords:   {initial_coords:,}")
    print(f"  Simplified coords: {final_coords:,}")
    print(f"  Coord reduction:   {coord_reduction:.1f}%")
    print(f"")
    print(f"  Properties kept:   All original properties")
    print(f"\n✓ Saved to {output_path}")


def simplify_api_layers():
    """Create simplified versions of all large API layers."""
    
    # Layers to simplify for API performance
    layers_to_simplify = [
        ('la_neighborhoods_comprehensive.geojson', 'la_neighborhoods_comprehensive_simplified.geojson'),
        ('la_county_cities.geojson', 'la_county_cities_simplified.geojson'),
        ('lacofd_station_boundaries.geojson', 'lacofd_station_boundaries_simplified.geojson'),
        ('lasd_station_boundaries.geojson', 'lasd_station_boundaries_simplified.geojson'),
        ('la_county_school_districts.geojson', 'la_county_school_districts_simplified.geojson'),
        ('la_county_election_precincts.geojson', 'la_county_election_precincts_simplified.geojson'),
        ('la_county_zip_codes.geojson', 'la_county_zip_codes_simplified.geojson'),
        ('la_city_neighborhood_councils.geojson', 'la_city_neighborhood_councils_simplified.geojson'),
    ]
    
    data_dir = Path('data/standard')
    
    print(f"\n{'='*70}")
    print("Creating Simplified GeoJSON Files for API Performance")
    print(f"{'='*70}\n")
    
    total_original = 0
    total_simplified = 0
    
    for input_file, output_file in layers_to_simplify:
        input_path = data_dir / input_file
        output_path = data_dir / output_file
        
        if not input_path.exists():
            print(f"⚠️  Skipping {input_file} (not found)")
            continue
        
        print(f"Processing {input_file}...")
        simplify_neighborhoods(input_path, output_path, tolerance=0.0001)
        
        original_size = input_path.stat().st_size / (1024 * 1024)
        simplified_size = output_path.stat().st_size / (1024 * 1024)
        
        total_original += original_size
        total_simplified += simplified_size
        print()
    
    print(f"\n{'='*70}")
    print("Summary:")
    print(f"{'='*70}")
    print(f"  Total original size:   {total_original:.2f} MB")
    print(f"  Total simplified size: {total_simplified:.2f} MB")
    print(f"  Total reduction:       {((total_original - total_simplified) / total_original * 100):.1f}%")
    print(f"\n✅ All layers simplified!")


def main():
    """Create simplified neighborhoods GeoJSON."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Create simplified version of GeoJSON files'
    )
    parser.add_argument(
        '--input',
        help='Input GeoJSON file'
    )
    parser.add_argument(
        '--output',
        help='Output GeoJSON file'
    )
    parser.add_argument(
        '--tolerance',
        type=float,
        default=0.0001,
        help='Simplification tolerance in degrees (default: 0.0001 ≈ 10-15m)'
    )
    parser.add_argument(
        '--api-layers',
        action='store_true',
        help='Simplify all large API layers'
    )
    
    args = parser.parse_args()
    
    if args.api_layers:
        simplify_api_layers()
        return
    
    if not args.input or not args.output:
        print("Error: --input and --output required (or use --api-layers)")
        sys.exit(1)
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    
    simplify_neighborhoods(input_path, output_path, args.tolerance)
    
    print(f"\n{'='*70}")
    print("Next steps:")
    print(f"{'='*70}")
    print("  1. Upload to S3:")
    print(f"     aws s3 cp {output_path} s3://stilesdata.com/la-geography/")
    print()
    print("  2. Access at:")
    print("     https://stilesdata.com/la-geography/la_neighborhoods_comprehensive_simplified.geojson")


if __name__ == "__main__":
    main()

