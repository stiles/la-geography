#!/usr/bin/env python3
"""
Fetch geographic boundaries for LA area from official sources.

Uses config/layers.yml for endpoint configuration.
Downloads from LA City GeoHub, LA County GIS Hub, and Caltrans.

Usage:
    python scripts/fetch_boundaries.py --out data/raw/
    python scripts/fetch_boundaries.py --out data/raw/ --layers lapd_bureaus la_city_boundary
"""

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import ezesri

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from geo_utils import (
    load_config,
    ensure_wgs84,
    normalize_columns,
    add_area_if_polygon,
    add_metadata,
    validate_bbox,
    fix_geometries,
    get_bbox_string,
)


def fetch_arcgis_layer(url: str, name: str) -> gpd.GeoDataFrame:
    """
    Fetch a layer from ArcGIS REST endpoint using ezesri.
    
    Args:
        url: ArcGIS REST service URL
        name: Layer name for logging
    
    Returns:
        GeoDataFrame with features
    """
    print(f"  Fetching from ArcGIS REST...")
    
    try:
        gdf = ezesri.extract_layer(url)
        print(f"  ✓ Retrieved {len(gdf)} features")
        return gdf
    except Exception as e:
        print(f"  ✗ Error fetching {name}: {e}")
        return None


def process_layer(layer_key: str, layer_config: dict) -> gpd.GeoDataFrame:
    """
    Fetch and process a single layer according to configuration.
    
    Args:
        layer_key: Layer identifier (e.g., 'lapd_bureaus')
        layer_config: Configuration dict from layers.yml
    
    Returns:
        Processed GeoDataFrame or None if fetch failed
    """
    print(f"\n{'='*60}")
    print(f"{layer_config['description']}")
    print(f"{'='*60}")
    
    # Fetch based on source type
    if layer_config['source'] == 'arcgis':
        gdf = fetch_arcgis_layer(layer_config['url'], layer_key)
    else:
        print(f"  ✗ Unknown source type: {layer_config['source']}")
        return None
    
    if gdf is None or len(gdf) == 0:
        print(f"  ✗ No data retrieved")
        return None
    
    # Normalize column names
    gdf = normalize_columns(gdf)
    
    # Ensure WGS84
    gdf = ensure_wgs84(gdf)
    
    # Fix invalid geometries
    gdf = fix_geometries(gdf)
    
    # Add area if polygons
    gdf = add_area_if_polygon(gdf)
    
    # Add metadata
    gdf = add_metadata(gdf, layer_config['url'])
    
    # Validate bbox
    if not validate_bbox(gdf):
        print(f"  ⚠ Bounding box outside expected LA County extent")
    
    # Check expected count if specified
    if 'expected_count' in layer_config and layer_config['expected_count']:
        expected = layer_config['expected_count']
        actual = len(gdf)
        tolerance = layer_config.get('expected_tolerance', 0)
        
        if abs(actual - expected) > tolerance:
            print(f"  ⚠ Feature count mismatch: expected {expected}±{tolerance}, got {actual}")
        else:
            print(f"  ✓ Feature count OK: {actual} (expected {expected}±{tolerance})")
    
    # Print bbox for reference
    bbox = get_bbox_string(gdf)
    print(f"  Bounds: {bbox}")
    
    return gdf


def validate_hierarchy(layers: dict) -> bool:
    """
    Validate LAPD hierarchy: reporting districts ≥ divisions ≥ bureaus.
    
    Args:
        layers: Dict of {layer_key: GeoDataFrame}
    
    Returns:
        True if hierarchy is valid
    """
    if not all(k in layers for k in ['lapd_bureaus', 'lapd_divisions', 'lapd_reporting_districts']):
        return True  # Skip if not all LAPD layers present
    
    bureaus = layers['lapd_bureaus']
    divisions = layers['lapd_divisions']
    districts = layers['lapd_reporting_districts']
    
    if all([bureaus is not None, divisions is not None, districts is not None]):
        if len(districts) >= len(divisions) >= len(bureaus):
            print(f"  ✓ LAPD hierarchy valid: {len(districts)} districts ≥ "
                  f"{len(divisions)} divisions ≥ {len(bureaus)} bureaus")
            return True
        else:
            print(f"  ⚠ LAPD hierarchy unexpected")
            return False
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Fetch geographic boundaries from official LA sources"
    )
    parser.add_argument(
        "--out",
        default="data/raw/",
        help="Output directory for raw GeoJSON files"
    )
    parser.add_argument(
        "--layers",
        nargs="+",
        help="Specific layers to fetch (default: all configured layers)"
    )
    parser.add_argument(
        "--config",
        default="config/layers.yml",
        help="Path to layer configuration file"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    print(f"Loading configuration from {args.config}...")
    config = load_config(args.config)
    
    # Filter layers if specified
    if args.layers:
        layers_to_fetch = {k: v for k, v in config.items() if k in args.layers}
        if not layers_to_fetch:
            print(f"✗ No matching layers found for: {', '.join(args.layers)}")
            sys.exit(1)
    else:
        layers_to_fetch = config
    
    print(f"Will fetch {len(layers_to_fetch)} layer(s): {', '.join(layers_to_fetch.keys())}")
    
    # Ensure output directory exists
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Fetch all configured layers
    print(f"\n{'='*60}")
    print("FETCHING LAYERS")
    print(f"{'='*60}")
    
    fetched = {}
    for layer_key, layer_config in layers_to_fetch.items():
        # Skip layers with missing URLs
        if layer_config['url'] == 'TO_BE_CONFIRMED':
            print(f"\n⚠ Skipping {layer_key}: URL not yet configured")
            continue
        
        gdf = process_layer(layer_key, layer_config)
        if gdf is not None:
            fetched[layer_key] = gdf
    
    # Validation
    print(f"\n{'='*60}")
    print("VALIDATION")
    print(f"{'='*60}")
    
    for layer_key, gdf in fetched.items():
        print(f"  ✓ {layer_key}: {len(gdf)} features")
    
    # LAPD hierarchy check
    validate_hierarchy(fetched)
    
    # Export to GeoJSON
    print(f"\n{'='*60}")
    print("EXPORTING")
    print(f"{'='*60}")
    
    for layer_key, gdf in fetched.items():
        output_path = out_dir / f"{layer_key}.geojson"
        print(f"  Writing {layer_key} → {output_path.name}")
        gdf.to_file(output_path, driver="GeoJSON")
    
    # Summary
    print(f"\n{'='*60}")
    print("✓ FETCH COMPLETE")
    print(f"{'='*60}")
    print(f"\nFetched {len(fetched)} layer(s)")
    print(f"Output directory: {out_dir.absolute()}")
    
    if len(fetched) < len(layers_to_fetch):
        skipped = len(layers_to_fetch) - len(fetched)
        print(f"\n⚠ {skipped} layer(s) skipped due to errors or missing configuration")


if __name__ == "__main__":
    main()

