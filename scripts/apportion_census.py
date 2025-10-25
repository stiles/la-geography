#!/usr/bin/env python3
"""
Apportion 2020 Census demographics to target polygon layers.

Uses area-weighted intersection to distribute Census block demographics
to any target polygon layer (e.g., LAPD divisions, neighborhoods, etc.).

Usage:
    # Apportion to a single layer
    python scripts/apportion_census.py --layer lapd_bureaus
    
    # Apportion to all polygon layers
    python scripts/apportion_census.py --all
    
    # Specify custom paths
    python scripts/apportion_census.py --layer lapd_divisions --input-dir data/standard
"""

import argparse
import sys
import warnings
from pathlib import Path
from datetime import datetime

import geopandas as gpd
import pandas as pd

# Suppress specific warnings
warnings.filterwarnings('ignore', category=FutureWarning)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from geo_utils import load_config, load_census_blocks, census_bbox_filter


def get_polygon_layers(config: dict) -> list:
    """
    Extract polygon layer names from config.
    
    Args:
        config: Loaded configuration dictionary
    
    Returns:
        List of polygon layer names
    """
    polygon_layers = []
    
    for layer_name, layer_config in config.items():
        if layer_name == 'census':
            continue
        
        if isinstance(layer_config, dict):
            geom_type = layer_config.get('geometry_type', '')
            if geom_type == 'polygon':
                polygon_layers.append(layer_name)
    
    return polygon_layers


def get_layer_id_field(layer_name: str, config: dict) -> str:
    """
    Get the ID field for a layer from config.
    
    Args:
        layer_name: Name of the layer
        config: Loaded configuration dictionary
    
    Returns:
        ID field name (or 'id' as fallback)
    """
    layer_config = config.get(layer_name, {})
    id_field = layer_config.get('id_field')
    
    # Handle null id_field in config
    if id_field is None or id_field == 'null':
        # Try to infer from name field or use generic 'id'
        name_field = layer_config.get('name_field')
        if name_field and name_field != 'null':
            return name_field
        return 'id'
    
    return id_field


def apportion_blocks_to_targets(
    blocks: gpd.GeoDataFrame,
    targets: gpd.GeoDataFrame,
    target_id_field: str,
    value_cols: list
) -> pd.DataFrame:
    """
    Apportion Census block values to target polygons using area weighting.
    
    Args:
        blocks: Census blocks GeoDataFrame with demographic columns
        targets: Target polygons GeoDataFrame
        target_id_field: Name of ID field in targets
        value_cols: List of demographic columns to apportion
    
    Returns:
        DataFrame with apportioned values by target ID
    """
    print(f"\n  Starting apportionment...")
    print(f"    Source blocks: {len(blocks):,}")
    print(f"    Target features: {len(targets):,}")
    print(f"    Value columns: {len(value_cols)}")
    
    # Ensure blocks have required columns
    missing_cols = [col for col in value_cols if col not in blocks.columns]
    if missing_cols:
        print(f"    ⚠ Missing columns in blocks: {missing_cols}")
        # Add missing columns with zeros
        for col in missing_cols:
            blocks[col] = 0
    
    # Reproject to California Albers (EPSG:3310) for accurate area calculation
    print(f"    Reprojecting to EPSG:3310...")
    blocks_proj = blocks.to_crs(3310)
    targets_proj = targets.to_crs(3310)
    
    # Add target ID if missing (e.g., for layers with null id_field)
    if target_id_field not in targets_proj.columns:
        targets_proj['target_id'] = range(len(targets_proj))
        target_id_field = 'target_id'
    
    # Intersect blocks with targets
    print(f"    Computing intersection...")
    intersected = gpd.overlay(blocks_proj, targets_proj, how='intersection')
    
    if len(intersected) == 0:
        print("    ⚠ No intersections found!")
        return pd.DataFrame()
    
    print(f"    Intersection features: {len(intersected):,}")
    
    # Calculate intersection areas
    intersected['intersection_area_m2'] = intersected.geometry.area
    
    # Calculate original block areas for weighting
    # Group by block_geoid to get total intersection area per block
    block_totals = intersected.groupby('block_geoid')['intersection_area_m2'].sum()
    
    # Calculate weight for each intersection piece
    intersected['weight'] = intersected.apply(
        lambda row: row['intersection_area_m2'] / block_totals[row['block_geoid']]
        if row['block_geoid'] in block_totals and block_totals[row['block_geoid']] > 0
        else 0,
        axis=1
    )
    
    # Apply weights to demographic values
    print(f"    Applying area weights...")
    for col in value_cols:
        if col in intersected.columns:
            intersected[f'{col}_weighted'] = intersected[col] * intersected['weight']
        else:
            intersected[f'{col}_weighted'] = 0
    
    # Aggregate by target ID
    print(f"    Aggregating by target...")
    weighted_cols = [f'{col}_weighted' for col in value_cols]
    
    # Identify descriptive columns from target layer to preserve
    # These are non-geometric, non-demographic columns
    preserve_cols = []
    exclude_cols = {'geometry', 'block_geoid', 'intersection_area_m2', 'weight', 'area_sqmi', 
                    'source_url', 'fetched_at'} | set(value_cols) | set(weighted_cols)
    
    for col in intersected.columns:
        if col not in exclude_cols and not col.startswith('pop_') and not col.startswith('housing_'):
            # Check if it's a target-layer column (same value for all rows of same target)
            if col != target_id_field and col in intersected.columns:
                preserve_cols.append(col)
    
    # Aggregate: sum for weighted demographic cols, first for descriptive cols
    agg_dict = {col: 'sum' for col in weighted_cols}
    agg_dict.update({col: 'first' for col in preserve_cols if col in intersected.columns})
    
    result = intersected.groupby(target_id_field).agg(agg_dict).reset_index()
    
    # Rename columns (remove _weighted suffix)
    rename_map = {f'{col}_weighted': col for col in value_cols}
    result = result.rename(columns=rename_map)
    
    # Add count of source blocks
    block_counts = intersected.groupby(target_id_field)['block_geoid'].nunique().reset_index()
    block_counts.columns = [target_id_field, 'source_blocks_count']
    result = result.merge(block_counts, on=target_id_field, how='left')
    
    print(f"    ✓ Apportionment complete")
    
    return result


def apportion_layer(
    layer_name: str,
    config: dict,
    input_dir: Path,
    output_dir: Path,
    census_blocks: gpd.GeoDataFrame
) -> bool:
    """
    Apportion Census data to a single layer.
    
    Args:
        layer_name: Name of the layer to process
        config: Loaded configuration dictionary
        input_dir: Directory containing standard layers
        output_dir: Directory for output demographics files
        census_blocks: Census blocks GeoDataFrame
    
    Returns:
        True if successful, False otherwise
    """
    print("\n" + "=" * 70)
    print(f"Processing: {layer_name}")
    print("=" * 70)
    
    # Load target layer
    layer_path = input_dir / f"{layer_name}.geojson"
    if not layer_path.exists():
        print(f"  ✗ Layer not found: {layer_path}")
        return False
    
    print(f"  Loading target layer: {layer_path}")
    targets = gpd.read_file(layer_path)
    print(f"    Features: {len(targets):,}")
    
    # Get ID field
    target_id_field = get_layer_id_field(layer_name, config)
    print(f"    ID field: {target_id_field}")
    
    # Filter blocks to target bbox for performance
    blocks_filtered = census_bbox_filter(census_blocks, targets)
    
    # Get demographic columns from config
    census_config = config.get('census', {})
    column_mapping = census_config.get('column_mapping', {})
    value_cols = list(column_mapping.values())
    
    # Apportion
    apportioned = apportion_blocks_to_targets(
        blocks_filtered,
        targets,
        target_id_field,
        value_cols
    )
    
    if len(apportioned) == 0:
        print(f"  ✗ Apportionment failed (no results)")
        return False
    
    # Add metadata
    apportioned['apportioned_at'] = datetime.now().isoformat()
    apportioned['census_vintage'] = 2020
    apportioned['source_layer'] = layer_name
    
    # Save to parquet
    output_path = output_dir / f"{layer_name}_demographics.parquet"
    apportioned.to_parquet(output_path)
    print(f"\n  ✓ Saved: {output_path}")
    
    # Print summary
    print(f"\n  Summary:")
    print(f"    Target features: {len(apportioned):,}")
    
    pop_col = 'pop_total'
    if pop_col in apportioned.columns:
        total_pop = apportioned[pop_col].sum()
        mean_pop = apportioned[pop_col].mean()
        print(f"    Total population: {total_pop:,.0f}")
        print(f"    Mean per feature: {mean_pop:,.0f}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Apportion 2020 Census demographics to polygon layers"
    )
    parser.add_argument(
        '--layer',
        help='Specific layer to process (e.g., lapd_bureaus)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all polygon layers'
    )
    parser.add_argument(
        '--config',
        default='config/layers.yml',
        help='Path to configuration file (default: config/layers.yml)'
    )
    parser.add_argument(
        '--input-dir',
        default='data/standard',
        help='Directory with target layers (default: data/standard)'
    )
    parser.add_argument(
        '--output-dir',
        default='data/standard',
        help='Directory for output demographics (default: data/standard)'
    )
    parser.add_argument(
        '--census-dir',
        default='data/census/processed',
        help='Directory with Census blocks (default: data/census/processed)'
    )
    
    args = parser.parse_args()
    
    if not args.layer and not args.all:
        parser.error("Must specify either --layer or --all")
    
    # Load configuration
    print("=" * 70)
    print("Census Apportionment - LA County 2020")
    print("=" * 70)
    
    config = load_config(args.config)
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load Census blocks
    print(f"\nLoading Census blocks from {args.census_dir}...")
    try:
        census_blocks = load_census_blocks(args.census_dir)
    except FileNotFoundError as e:
        print(f"\n✗ {e}")
        print("\nPlease run 'make fetch-census' first to download Census data.")
        sys.exit(1)
    
    # Determine layers to process
    if args.all:
        layers_to_process = get_polygon_layers(config)
        print(f"\nProcessing all {len(layers_to_process)} polygon layers")
    else:
        layers_to_process = [args.layer]
        print(f"\nProcessing single layer: {args.layer}")
    
    # Process each layer
    results = {}
    for layer_name in layers_to_process:
        success = apportion_layer(
            layer_name,
            config,
            input_dir,
            output_dir,
            census_blocks
        )
        results[layer_name] = success
    
    # Print final summary
    print("\n" + "=" * 70)
    print("Final Summary")
    print("=" * 70)
    
    successful = [name for name, success in results.items() if success]
    failed = [name for name, success in results.items() if not success]
    
    print(f"\n✓ Successful: {len(successful)}/{len(results)}")
    if successful:
        for name in successful:
            print(f"    - {name}")
    
    if failed:
        print(f"\n✗ Failed: {len(failed)}/{len(results)}")
        for name in failed:
            print(f"    - {name}")
    
    print("\n" + "=" * 70)
    
    if failed:
        sys.exit(1)


if __name__ == '__main__':
    main()

