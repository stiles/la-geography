"""
Enrich GeoJSON files with demographic data.

Takes a GeoJSON file and its companion demographics parquet file and creates
a new GeoJSON file with the demographic fields embedded in the feature properties.

This is useful for APIs that need to return demographics without doing runtime joins.
"""

import json
from pathlib import Path
import pandas as pd
import geopandas as gpd
import yaml
from typing import Optional


def load_config() -> dict:
    """Load layer configuration."""
    config_path = Path(__file__).parent.parent / 'config' / 'layers.yml'
    with open(config_path) as f:
        return yaml.safe_load(f)


def enrich_geojson(
    layer_name: str,
    input_dir: Path,
    output_dir: Path,
    config: dict,
    demographic_fields: Optional[list] = None
) -> bool:
    """
    Enrich a GeoJSON file with demographics.
    
    Args:
        layer_name: Name of the layer
        input_dir: Directory containing input files
        output_dir: Directory for output files
        config: Configuration dictionary
        demographic_fields: List of demographic fields to include (default: all pop_* and housing_*)
    
    Returns:
        True if successful, False otherwise
    """
    print(f"\nEnriching {layer_name}...")
    
    # Get file paths
    geojson_path = input_dir / f"{layer_name}.geojson"
    demo_path = input_dir / f"{layer_name}_demographics.parquet"
    output_path = output_dir / f"{layer_name}.geojson"
    
    # Check if files exist
    if not geojson_path.exists():
        print(f"  ✗ GeoJSON not found: {geojson_path}")
        return False
    
    if not demo_path.exists():
        print(f"  ℹ No demographics file found, skipping: {demo_path}")
        return False
    
    # Load data
    print(f"  Loading {geojson_path.name}...")
    gdf = gpd.read_file(geojson_path)
    
    print(f"  Loading {demo_path.name}...")
    demographics = pd.read_parquet(demo_path)
    
    # Get ID field from config
    layer_config = config.get(layer_name, {})
    id_field = layer_config.get('id_field')
    
    if not id_field or id_field == 'null':
        print(f"  ✗ No id_field configured for {layer_name}")
        return False
    
    # Verify ID field exists
    if id_field not in gdf.columns:
        print(f"  ✗ ID field '{id_field}' not found in GeoJSON")
        return False
    
    if id_field not in demographics.columns:
        print(f"  ✗ ID field '{id_field}' not found in demographics")
        return False
    
    # Determine which demographic fields to include
    if demographic_fields is None:
        demographic_fields = [
            col for col in demographics.columns
            if col.startswith('pop_') or col.startswith('housing_')
        ]
    
    # Keep only relevant columns from demographics
    demo_cols = [id_field] + demographic_fields
    demographics_clean = demographics[demo_cols].copy()
    
    # Join demographics to GeoJSON
    print(f"  Joining on '{id_field}'...")
    enriched = gdf.merge(demographics_clean, on=id_field, how='left')
    
    # Check for unmatched features
    unmatched = enriched[enriched['pop_total'].isna()]
    if len(unmatched) > 0:
        print(f"  ⚠ Warning: {len(unmatched)} features did not match demographics")
    
    # Save enriched GeoJSON
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Writing to {output_path}...")
    enriched.to_file(output_path, driver='GeoJSON')
    
    # Report statistics
    original_size = geojson_path.stat().st_size / 1024 / 1024
    enriched_size = output_path.stat().st_size / 1024 / 1024
    increase_pct = ((enriched_size - original_size) / original_size) * 100
    
    print(f"  ✓ Success!")
    print(f"    Original: {original_size:.2f} MB")
    print(f"    Enriched: {enriched_size:.2f} MB (+{increase_pct:.1f}%)")
    print(f"    Features: {len(enriched)}")
    print(f"    Added fields: {', '.join(demographic_fields)}")
    
    return True


def main():
    """Enrich specified layers with demographics."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enrich GeoJSON files with demographics')
    parser.add_argument(
        '--layers',
        nargs='+',
        help='Layer names to enrich (default: key layers for API)'
    )
    parser.add_argument(
        '--input-dir',
        default='data/standard',
        help='Input directory (default: data/standard)'
    )
    parser.add_argument(
        '--output-dir',
        default='data/enriched',
        help='Output directory (default: data/enriched)'
    )
    
    args = parser.parse_args()
    
    # Default layers for API enrichment
    if not args.layers:
        args.layers = [
            'la_neighborhoods_comprehensive',
            'la_regions',
            'la_county_cities',
        ]
    
    # Setup paths
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    # Load config
    print("Loading configuration...")
    config = load_config()
    
    # Process each layer
    success_count = 0
    for layer_name in args.layers:
        if enrich_geojson(layer_name, input_dir, output_dir, config):
            success_count += 1
    
    print(f"\n{'=' * 70}")
    print(f"Enriched {success_count}/{len(args.layers)} layers")
    print(f"Output directory: {output_dir}")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    main()

