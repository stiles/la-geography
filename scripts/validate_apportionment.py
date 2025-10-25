#!/usr/bin/env python3
"""
Validate Census apportionment results.

Checks that:
- Population totals are conserved (within tolerance)
- No negative values
- All target features have demographic data
- Totals match known benchmarks (LA City ~3.9M, LA County ~10.0M)

Usage:
    # Validate a specific layer
    python scripts/validate_apportionment.py --layer lapd_bureaus
    
    # Validate all layers
    python scripts/validate_apportionment.py --all
    
    # Set custom tolerance
    python scripts/validate_apportionment.py --all --tolerance 2.0
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import geopandas as gpd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from geo_utils import load_config, load_census_blocks, validate_apportionment


# Known population benchmarks (2020 Census)
BENCHMARKS = {
    'la_county_boundary': {
        'pop_total': 10_014_009,
        'tolerance_pct': 0.1,  # Should be very close
        'description': 'LA County'
    },
    'la_city_boundary': {
        'pop_total': 3_898_747,
        'tolerance_pct': 2.5,  # GeoHub boundary extends slightly beyond Census definition
        'description': 'City of Los Angeles'
    }
}


def get_polygon_layers(config: dict) -> list:
    """Extract polygon layer names from config."""
    polygon_layers = []
    
    for layer_name, layer_config in config.items():
        if layer_name == 'census':
            continue
        
        if isinstance(layer_config, dict):
            geom_type = layer_config.get('geometry_type', '')
            if geom_type == 'polygon':
                polygon_layers.append(layer_name)
    
    return polygon_layers


def validate_layer(
    layer_name: str,
    demographics_path: Path,
    data_dir: Path,
    census_blocks: gpd.GeoDataFrame,
    value_cols: list,
    tolerance_pct: float
) -> dict:
    """
    Validate apportionment for a single layer.
    
    Args:
        layer_name: Name of the layer
        demographics_path: Path to demographics parquet file
        data_dir: Directory with target layers
        census_blocks: Census blocks GeoDataFrame
        value_cols: List of demographic columns
        tolerance_pct: Tolerance percentage for validation
    
    Returns:
        Dictionary with validation results
    """
    print("\n" + "=" * 70)
    print(f"Validating: {layer_name}")
    print("=" * 70)
    
    if not demographics_path.exists():
        print(f"  ✗ File not found: {demographics_path}")
        return {'valid': False, 'reason': 'file_not_found'}
    
    # Load apportioned data
    apportioned = pd.read_parquet(demographics_path)
    print(f"  Features: {len(apportioned):,}")
    
    # Check for negative values
    has_negatives = False
    for col in value_cols:
        if col in apportioned.columns:
            neg_count = (apportioned[col] < 0).sum()
            if neg_count > 0:
                print(f"  ✗ Found {neg_count} negative values in {col}")
                has_negatives = True
    
    if not has_negatives:
        print(f"  ✓ No negative values")
    
    # Check for missing values
    has_nulls = False
    for col in value_cols:
        if col in apportioned.columns:
            null_count = apportioned[col].isna().sum()
            if null_count > 0:
                print(f"  ⚠ Found {null_count} null values in {col}")
                has_nulls = True
    
    if not has_nulls:
        print(f"  ✓ No null values")
    
    # Load target layer to filter Census blocks appropriately
    layer_path = data_dir / f"{layer_name}.geojson"
    if not layer_path.exists():
        print(f"  ⚠ Cannot load target layer for validation: {layer_path}")
        # Skip conservation check if we can't load the layer
        conservation_valid = True
    else:
        # Load target layer
        targets = gpd.read_file(layer_path)
        
        # Filter Census blocks to only those that intersect the target layer
        # This is important because many layers cover only part of LA County
        print(f"  Filtering Census blocks to target area...")
        
        # Use bbox filter first for performance
        from geo_utils import census_bbox_filter
        blocks_filtered = census_bbox_filter(census_blocks, targets, buffer_deg=0.01)
        
        # Now do actual intersection to get only blocks that truly overlap
        # Use a small buffer to catch edge cases
        from shapely import union_all
        targets_geoms = targets.to_crs(blocks_filtered.crs).geometry.tolist()
        targets_union = union_all(targets_geoms)
        blocks_relevant = blocks_filtered[blocks_filtered.intersects(targets_union)]
        
        print(f"    Relevant blocks: {len(blocks_relevant):,} (of {len(census_blocks):,} total)")
        
        # Validate conservation of totals against ONLY the relevant blocks
        apportioned_totals = {}
        for col in value_cols:
            if col in apportioned.columns:
                apportioned_totals[col] = apportioned[col].sum()
        
        conservation_valid = validate_apportionment(
            blocks_relevant,
            apportioned_totals,
            value_cols,
            tolerance_pct
        )
    
    # Check against known benchmarks
    benchmark_valid = True
    if layer_name in BENCHMARKS:
        benchmark = BENCHMARKS[layer_name]
        print(f"\n  Benchmark check: {benchmark['description']}")
        
        if 'pop_total' in apportioned.columns:
            actual = apportioned['pop_total'].sum()
            expected = benchmark['pop_total']
            diff_pct = abs(actual - expected) / expected * 100
            
            bench_tolerance = benchmark.get('tolerance_pct', tolerance_pct)
            
            if diff_pct <= bench_tolerance:
                print(f"    ✓ Population: {actual:,.0f} "
                      f"(expected {expected:,.0f}, diff {diff_pct:.2f}%)")
            else:
                print(f"    ✗ Population: {actual:,.0f} "
                      f"(expected {expected:,.0f}, diff {diff_pct:.2f}%)")
                benchmark_valid = False
    
    # Overall validation
    is_valid = (
        not has_negatives and
        not has_nulls and
        conservation_valid and
        benchmark_valid
    )
    
    if is_valid:
        print(f"\n  ✓ Validation PASSED")
    else:
        print(f"\n  ✗ Validation FAILED")
    
    return {
        'valid': is_valid,
        'has_negatives': has_negatives,
        'has_nulls': has_nulls,
        'conservation_valid': conservation_valid,
        'benchmark_valid': benchmark_valid
    }


def main():
    parser = argparse.ArgumentParser(
        description="Validate Census apportionment results"
    )
    parser.add_argument(
        '--layer',
        help='Specific layer to validate (e.g., lapd_bureaus)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Validate all polygon layers'
    )
    parser.add_argument(
        '--config',
        default='config/layers.yml',
        help='Path to configuration file (default: config/layers.yml)'
    )
    parser.add_argument(
        '--data-dir',
        default='data/standard',
        help='Directory with demographics files (default: data/standard)'
    )
    parser.add_argument(
        '--census-dir',
        default='data/census/processed',
        help='Directory with Census blocks (default: data/census/processed)'
    )
    parser.add_argument(
        '--tolerance',
        type=float,
        default=1.0,
        help='Tolerance percentage for validation (default: 1.0)'
    )
    
    args = parser.parse_args()
    
    if not args.layer and not args.all:
        parser.error("Must specify either --layer or --all")
    
    # Load configuration
    print("=" * 70)
    print("Census Apportionment Validation")
    print("=" * 70)
    print(f"\nTolerance: {args.tolerance}%")
    
    config = load_config(args.config)
    
    data_dir = Path(args.data_dir)
    
    # Load Census blocks for validation
    print(f"\nLoading Census blocks...")
    try:
        census_blocks = load_census_blocks(args.census_dir)
    except FileNotFoundError as e:
        print(f"\n✗ {e}")
        sys.exit(1)
    
    # Get demographic columns
    census_config = config.get('census', {})
    column_mapping = census_config.get('column_mapping', {})
    value_cols = list(column_mapping.values())
    
    # Determine layers to validate
    if args.all:
        layers_to_validate = get_polygon_layers(config)
        print(f"\nValidating {len(layers_to_validate)} polygon layers")
    else:
        layers_to_validate = [args.layer]
        print(f"\nValidating single layer: {args.layer}")
    
    # Validate each layer
    results = {}
    for layer_name in layers_to_validate:
        demographics_path = data_dir / f"{layer_name}_demographics.parquet"
        result = validate_layer(
            layer_name,
            demographics_path,
            data_dir,
            census_blocks,
            value_cols,
            args.tolerance
        )
        results[layer_name] = result
    
    # Print final summary
    print("\n" + "=" * 70)
    print("Validation Summary")
    print("=" * 70)
    
    passed = [name for name, result in results.items() if result.get('valid', False)]
    failed = [name for name, result in results.items() if not result.get('valid', False)]
    
    print(f"\n✓ Passed: {len(passed)}/{len(results)}")
    if passed:
        for name in passed:
            print(f"    - {name}")
    
    if failed:
        print(f"\n✗ Failed: {len(failed)}/{len(results)}")
        for name in failed:
            result = results[name]
            reasons = []
            if result.get('reason'):
                reasons.append(result['reason'])
            if result.get('has_negatives'):
                reasons.append('negative values')
            if result.get('has_nulls'):
                reasons.append('null values')
            if not result.get('conservation_valid'):
                reasons.append('conservation failed')
            if not result.get('benchmark_valid'):
                reasons.append('benchmark failed')
            
            reason_str = ', '.join(reasons) if reasons else 'unknown'
            print(f"    - {name} ({reason_str})")
    
    print("\n" + "=" * 70)
    
    if failed:
        sys.exit(1)
    else:
        print("\n✓ All validations passed!")


if __name__ == '__main__':
    main()

