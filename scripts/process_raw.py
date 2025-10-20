#!/usr/bin/env python3
"""
Process raw boundary data to fix known issues.

Handles:
1. LA County Boundary - Filter and dissolve
2. LA Freeways - Clip to LA County
3. LA County Cities - Keep as-is for manual QGIS review

Usage:
    python scripts/process_raw.py --input data/raw/ --output data/standard/
    python scripts/process_raw.py --input data/raw/ --output data/standard/ --layer la_county_boundary
"""

import argparse
import sys
from pathlib import Path

import geopandas as gpd

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from geo_utils import (
    ensure_wgs84,
    add_area_if_polygon,
    get_bbox_string,
)


def process_la_county_boundary(input_path: Path, output_path: Path) -> None:
    """
    Process LA County boundary: Filter to LA County only and dissolve.
    
    Input: 11 features (LA County + 8 neighboring counties)
    Output: 1 feature (LA County mainland + islands dissolved)
    """
    print(f"\n{'='*60}")
    print("Processing: LA County Boundary")
    print(f"{'='*60}")
    
    # Read raw data
    gdf = gpd.read_file(input_path)
    print(f"  Input: {len(gdf)} features")
    
    # Show what we have
    print("\n  Before filtering:")
    for _, row in gdf.iterrows():
        print(f"    - {row['name']}: {row['area_sqmi']:.2f} sq mi (TYPE: {row['type']})")
    
    # Filter to LA County only (name == "LOS ANGELES COUNTY")
    print(f"\n  Filtering to name == 'LOS ANGELES COUNTY'...")
    gdf_filtered = gdf[gdf['name'] == 'LOS ANGELES COUNTY'].copy()
    print(f"  After filter: {len(gdf_filtered)} features")
    
    if len(gdf_filtered) == 0:
        print("  ✗ No features match 'LOS ANGELES COUNTY'")
        print(f"  Available names: {gdf['name'].unique().tolist()}")
        return
    
    # Show the pieces
    print("\n  LA County pieces:")
    for idx, row in gdf_filtered.iterrows():
        print(f"    - {row['area_sqmi']:.2f} sq mi")
    print(f"  Total area: {gdf_filtered['area_sqmi'].sum():.2f} sq mi")
    
    # Dissolve into single feature
    print("\n  Dissolving into single feature...")
    gdf_dissolved = gdf_filtered.dissolve()
    
    # Reset index and clean up
    gdf_dissolved = gdf_dissolved.reset_index(drop=True)
    
    # Keep only essential fields
    gdf_dissolved = gdf_dissolved[['name', 'geometry']]
    
    # Recalculate area after dissolve
    gdf_dissolved = add_area_if_polygon(gdf_dissolved)
    
    # Ensure WGS84
    gdf_dissolved = ensure_wgs84(gdf_dissolved)
    
    print(f"  Output: {len(gdf_dissolved)} feature(s)")
    print(f"  Total area: {gdf_dissolved['area_sqmi'].iloc[0]:.2f} sq mi")
    print(f"  Bounds: {get_bbox_string(gdf_dissolved)}")
    
    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf_dissolved.to_file(output_path, driver="GeoJSON")
    print(f"  ✓ Saved to {output_path}")


def process_la_freeways(
    input_path: Path,
    output_path: Path,
    county_boundary_path: Path
) -> None:
    """
    Process LA Freeways: Clip to LA County boundary.
    
    Input: 5,430 features (entire California)
    Output: ~50-150 features (LA County only)
    """
    print(f"\n{'='*60}")
    print("Processing: LA Freeways")
    print(f"{'='*60}")
    
    # Check if county boundary exists
    if not county_boundary_path.exists():
        print(f"  ✗ County boundary not found: {county_boundary_path}")
        print(f"  Run this script with --layer la_county_boundary first")
        return
    
    # Read freeways (statewide)
    print(f"  Loading freeways...")
    freeways = gpd.read_file(input_path)
    print(f"  Input: {len(freeways)} features (entire California)")
    print(f"  Bounds: {get_bbox_string(freeways)}")
    
    # Read LA County boundary
    print(f"\n  Loading LA County boundary...")
    county = gpd.read_file(county_boundary_path)
    print(f"  County area: {county['area_sqmi'].iloc[0]:.2f} sq mi")
    
    # Ensure same CRS
    if freeways.crs != county.crs:
        print(f"  Reprojecting county boundary to match freeways CRS...")
        county = county.to_crs(freeways.crs)
    
    # Clip to county boundary
    print(f"\n  Clipping to LA County boundary...")
    freeways_clipped = gpd.clip(freeways, county)
    print(f"  After clip: {len(freeways_clipped)} features")
    
    # Show breakdown by NHS type before filtering
    if 'nhs_type' in freeways_clipped.columns:
        print(f"\n  Before filtering - NHS types:")
        for nhs_type, count in freeways_clipped['nhs_type'].value_counts().items():
            print(f"    - {nhs_type}: {count} segments")
    
    # Filter to Interstates and State Highways only
    print(f"\n  Filtering to Interstates and State Highways (SHS)...")
    print(f"    Criteria: nhs_type == 'INTERSTATE' OR routeid contains 'SHS'")
    
    mask = (
        (freeways_clipped['nhs_type'] == 'INTERSTATE') |
        (freeways_clipped['routeid'].str.contains('SHS', na=False))
    )
    freeways_filtered = freeways_clipped[mask].copy()
    
    print(f"  After filter: {len(freeways_filtered)} features")
    print(f"  Bounds: {get_bbox_string(freeways_filtered)}")
    
    # Show breakdown after filtering
    if 'nhs_type' in freeways_filtered.columns:
        print(f"\n  After filtering - NHS types:")
        for nhs_type, count in freeways_filtered['nhs_type'].value_counts().items():
            print(f"    - {nhs_type}: {count} segments")
    
    # Show some example route IDs
    if len(freeways_filtered) > 0:
        print(f"\n  Sample route IDs:")
        sample_routes = freeways_filtered['routeid'].value_counts().head(10)
        for route, count in sample_routes.items():
            nhs = freeways_filtered[freeways_filtered['routeid'] == route]['nhs_type'].iloc[0]
            print(f"    - {route} ({nhs}): {count} segments")
    
    # Ensure WGS84
    freeways_filtered = ensure_wgs84(freeways_filtered)
    
    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    freeways_filtered.to_file(output_path, driver="GeoJSON")
    print(f"  ✓ Saved to {output_path}")


def process_la_county_cities(input_path: Path, output_path: Path) -> None:
    """
    Process LA County cities: Filter to land features and dissolve by city name.
    
    This layer includes water features (piers, breakwaters) and has fragmented
    cities/unincorporated areas. Filter to land only and dissolve.
    
    Input: 347 features (cities + unincorporated + water features)
    Output: ~88 features (one per city/community, land only)
    """
    print(f"\n{'='*60}")
    print("Processing: LA County Cities")
    print(f"{'='*60}")
    
    gdf = gpd.read_file(input_path)
    
    print(f"  Input: {len(gdf)} features")
    
    # Show breakdown before filtering
    print(f"\n  Before filtering:")
    print(f"    feat_type breakdown:")
    for feat_type, count in gdf['feat_type'].value_counts().items():
        print(f"      - {feat_type}: {count} features")
    
    print(f"    city_type breakdown:")
    for city_type, count in gdf['city_type'].value_counts().items():
        total_area = gdf[gdf['city_type'] == city_type]['area_sqmi'].sum()
        print(f"      - {city_type}: {count} features ({total_area:.2f} sq mi)")
    
    # Filter to land features only (exclude piers, breakwaters, etc.)
    print(f"\n  Filtering to feat_type == 'Land'...")
    gdf_land = gdf[gdf['feat_type'] == 'Land'].copy()
    print(f"  After filter: {len(gdf_land)} features")
    
    # Drop unnecessary columns
    print(f"\n  Dropping unnecessary columns...")
    keep_cols = ['city_name', 'city_type', 'city_label', 'abbr', 'geometry']
    # Keep only columns that exist
    keep_cols = [col for col in keep_cols if col in gdf_land.columns]
    gdf_clean = gdf_land[keep_cols].copy()
    
    # Add area before dissolving (will recalculate after)
    gdf_clean = add_area_if_polygon(gdf_clean)
    
    print(f"  Kept columns: {', '.join(keep_cols)}")
    print(f"  Total area before dissolve: {gdf_clean['area_sqmi'].sum():.2f} sq mi")
    
    # Dissolve by city_name
    print(f"\n  Dissolving by city_name...")
    gdf_dissolved = gdf_clean.dissolve(by='city_name', aggfunc='first')
    gdf_dissolved = gdf_dissolved.reset_index()
    
    print(f"  Output: {len(gdf_dissolved)} features")
    
    # Recalculate area after dissolve
    gdf_dissolved = add_area_if_polygon(gdf_dissolved)
    
    # Show results
    print(f"  Total area after dissolve: {gdf_dissolved['area_sqmi'].sum():.2f} sq mi")
    
    print(f"\n  Largest 10 by area:")
    for _, row in gdf_dissolved.nlargest(10, 'area_sqmi')[['city_name', 'city_type', 'area_sqmi']].iterrows():
        print(f"    - {row['city_name']} ({row['city_type']}): {row['area_sqmi']:.2f} sq mi")
    
    print(f"\n  Breakdown by city_type:")
    for city_type in gdf_dissolved['city_type'].unique():
        subset = gdf_dissolved[gdf_dissolved['city_type'] == city_type]
        print(f"    - {city_type}: {len(subset)} features ({subset['area_sqmi'].sum():.2f} sq mi)")
    
    # Ensure WGS84
    gdf_dissolved = ensure_wgs84(gdf_dissolved)
    
    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf_dissolved.to_file(output_path, driver="GeoJSON")
    print(f"  ✓ Saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Process raw boundary data to fix known issues"
    )
    parser.add_argument(
        "--input",
        default="data/raw/",
        help="Input directory with raw GeoJSON files"
    )
    parser.add_argument(
        "--output",
        default="data/standard/",
        help="Output directory for processed files"
    )
    parser.add_argument(
        "--layer",
        choices=["la_county_boundary", "la_freeways", "la_county_cities", "all"],
        default="all",
        help="Specific layer to process (default: all)"
    )
    
    args = parser.parse_args()
    
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    
    # Ensure directories exist
    if not input_dir.exists():
        print(f"✗ Input directory not found: {input_dir}")
        sys.exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"{'='*60}")
    print("RAW DATA PROCESSING")
    print(f"{'='*60}")
    print(f"Input:  {input_dir.absolute()}")
    print(f"Output: {output_dir.absolute()}")
    
    # Process layers
    if args.layer in ["la_county_boundary", "all"]:
        input_path = input_dir / "la_county_boundary.geojson"
        output_path = output_dir / "la_county_boundary.geojson"
        
        if input_path.exists():
            process_la_county_boundary(input_path, output_path)
        else:
            print(f"\n⚠️  Skipping la_county_boundary: {input_path} not found")
    
    if args.layer in ["la_county_cities", "all"]:
        input_path = input_dir / "la_county_cities.geojson"
        output_path = output_dir / "la_county_cities.geojson"
        
        if input_path.exists():
            process_la_county_cities(input_path, output_path)
        else:
            print(f"\n⚠️  Skipping la_county_cities: {input_path} not found")
    
    if args.layer in ["la_freeways", "all"]:
        input_path = input_dir / "la_freeways.geojson"
        output_path = output_dir / "la_freeways.geojson"
        county_path = output_dir / "la_county_boundary.geojson"
        
        if input_path.exists():
            process_la_freeways(input_path, output_path, county_path)
        else:
            print(f"\n⚠️  Skipping la_freeways: {input_path} not found")
    
    print(f"\n{'='*60}")
    print("✓ PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"\nProcessed files saved to: {output_dir.absolute()}")


if __name__ == "__main__":
    main()

