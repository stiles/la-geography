#!/usr/bin/env python3
"""
Data loader utilities for LA Geography project.

Convenient functions for loading boundary layers with optional demographics.
Supports both local file paths and direct S3 URLs.

Usage:
    from scripts.data_loader import load_layer, load_layer_with_demographics
    
    # Load boundaries only
    boundaries = load_layer('lapd_divisions')
    
    # Load boundaries with demographics pre-joined
    enriched = load_layer_with_demographics('lapd_divisions')
    
    # Load from S3 directly
    boundaries = load_layer('lapd_divisions', 
                           base_url='https://stilesdata.com/la-geography')
"""

import sys
from pathlib import Path
from typing import Optional, Union

import geopandas as gpd
import pandas as pd
import yaml


def load_config(config_path: Union[str, Path] = 'config/layers.yml') -> dict:
    """
    Load layer configuration from YAML file.
    
    Args:
        config_path: Path to layers.yml configuration file
        
    Returns:
        Configuration dictionary
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_layer_id_field(layer_name: str, config: Optional[dict] = None) -> str:
    """
    Get the ID field for a layer from configuration.
    
    Args:
        layer_name: Name of the layer
        config: Optional pre-loaded configuration dictionary
        
    Returns:
        ID field name for joining demographics
    """
    if config is None:
        config = load_config()
    
    layer_config = config.get(layer_name, {})
    id_field = layer_config.get('id_field')
    
    # Handle null id_field in config
    if id_field is None or id_field == 'null':
        # Try name_field as fallback
        name_field = layer_config.get('name_field')
        if name_field and name_field != 'null':
            return name_field
        # Last resort: generic 'id'
        return 'id'
    
    return id_field


def load_layer(
    layer_name: str,
    data_dir: Optional[Union[str, Path]] = None,
    base_url: Optional[str] = None
) -> gpd.GeoDataFrame:
    """
    Load a boundary layer (GeoJSON).
    
    Args:
        layer_name: Name of the layer (e.g., 'lapd_divisions')
        data_dir: Local directory containing GeoJSON files (default: 'data/standard')
        base_url: Base URL for remote files (e.g., 'https://stilesdata.com/la-geography')
                 If provided, overrides data_dir
        
    Returns:
        GeoDataFrame with boundary geometries
        
    Examples:
        # Load from local directory
        gdf = load_layer('lapd_divisions')
        
        # Load from S3
        gdf = load_layer('lapd_divisions', 
                        base_url='https://stilesdata.com/la-geography')
    """
    if base_url:
        # Load from remote URL
        file_path = f"{base_url.rstrip('/')}/{layer_name}.geojson"
    else:
        # Load from local directory
        if data_dir is None:
            data_dir = Path('data/standard')
        else:
            data_dir = Path(data_dir)
        
        file_path = data_dir / f"{layer_name}.geojson"
        
        if not file_path.exists():
            raise FileNotFoundError(
                f"Layer file not found: {file_path}\n"
                f"Make sure you've run 'make fetch' and 'make standardize' first, "
                f"or use base_url to load from S3."
            )
    
    try:
        return gpd.read_file(file_path)
    except Exception as e:
        raise ValueError(f"Failed to load layer '{layer_name}': {e}")


def load_demographics(
    layer_name: str,
    data_dir: Optional[Union[str, Path]] = None,
    base_url: Optional[str] = None
) -> pd.DataFrame:
    """
    Load demographics for a layer (Parquet format).
    
    Args:
        layer_name: Name of the layer (e.g., 'lapd_divisions')
        data_dir: Local directory containing Parquet files (default: 'data/standard')
        base_url: Base URL for remote files (e.g., 'https://stilesdata.com/la-geography')
                 If provided, overrides data_dir
        
    Returns:
        DataFrame with demographic data
        
    Raises:
        FileNotFoundError: If demographics file doesn't exist
        
    Examples:
        # Load from local directory
        demo = load_demographics('lapd_divisions')
        
        # Load from S3
        demo = load_demographics('lapd_divisions',
                                base_url='https://stilesdata.com/la-geography')
    """
    if base_url:
        # Load from remote URL
        file_path = f"{base_url.rstrip('/')}/{layer_name}_demographics.parquet"
    else:
        # Load from local directory
        if data_dir is None:
            data_dir = Path('data/standard')
        else:
            data_dir = Path(data_dir)
        
        file_path = data_dir / f"{layer_name}_demographics.parquet"
        
        if not file_path.exists():
            raise FileNotFoundError(
                f"Demographics file not found: {file_path}\n"
                f"Run 'make fetch-census' and 'make apportion-census' to generate demographics, "
                f"or use base_url to load from S3."
            )
    
    try:
        return pd.read_parquet(file_path)
    except Exception as e:
        raise ValueError(f"Failed to load demographics for '{layer_name}': {e}")


def load_layer_with_demographics(
    layer_name: str,
    data_dir: Optional[Union[str, Path]] = None,
    base_url: Optional[str] = None,
    config: Optional[dict] = None,
    require_demographics: bool = False
) -> gpd.GeoDataFrame:
    """
    Load a boundary layer with demographics pre-joined.
    
    This is the recommended way to load layers with demographics - it handles
    the join automatically using the correct ID field from configuration.
    
    Args:
        layer_name: Name of the layer (e.g., 'lapd_divisions')
        data_dir: Local directory containing files (default: 'data/standard')
        base_url: Base URL for remote files (e.g., 'https://stilesdata.com/la-geography')
                 If provided, overrides data_dir
        config: Optional pre-loaded configuration dictionary
        require_demographics: If True, raises error if demographics don't exist.
                            If False, returns boundaries only (default)
        
    Returns:
        GeoDataFrame with boundaries and demographics joined
        
    Examples:
        # Load from local directory
        enriched = load_layer_with_demographics('lapd_divisions')
        
        # Load from S3
        enriched = load_layer_with_demographics(
            'lapd_divisions',
            base_url='https://stilesdata.com/la-geography'
        )
        
        # Require demographics (error if missing)
        enriched = load_layer_with_demographics('lapd_divisions', 
                                               require_demographics=True)
    """
    # Load boundaries
    boundaries = load_layer(layer_name, data_dir=data_dir, base_url=base_url)
    
    # Try to load demographics
    try:
        demographics = load_demographics(layer_name, data_dir=data_dir, base_url=base_url)
    except FileNotFoundError:
        if require_demographics:
            raise
        else:
            print(f"Note: Demographics not available for '{layer_name}'. Returning boundaries only.")
            return boundaries
    
    # Get ID field for joining
    if config is None:
        try:
            config = load_config()
        except FileNotFoundError:
            # If config not available, try common ID fields
            print("Warning: Could not load config. Attempting join with common ID fields.")
            for potential_id in ['id', 'slug', 'prec', 'district', 'bureau', 'objectid', 'name']:
                if potential_id in boundaries.columns and potential_id in demographics.columns:
                    id_field = potential_id
                    print(f"Using ID field: {id_field}")
                    break
            else:
                raise ValueError(
                    f"Could not determine ID field for joining. "
                    f"Boundaries columns: {list(boundaries.columns)}, "
                    f"Demographics columns: {list(demographics.columns)}"
                )
    else:
        id_field = get_layer_id_field(layer_name, config)
    
    # Verify ID field exists in both dataframes
    if id_field not in boundaries.columns:
        raise ValueError(
            f"ID field '{id_field}' not found in boundaries. "
            f"Available columns: {list(boundaries.columns)}"
        )
    
    if id_field not in demographics.columns:
        raise ValueError(
            f"ID field '{id_field}' not found in demographics. "
            f"Available columns: {list(demographics.columns)}"
        )
    
    # Join demographics to boundaries
    enriched = boundaries.merge(demographics, on=id_field, how='left')
    
    # Check for unmatched features
    unmatched = enriched[enriched['pop_total'].isna()]
    if len(unmatched) > 0:
        print(f"Warning: {len(unmatched)} features did not match demographics data")
    
    return enriched


# Convenience function for backwards compatibility with existing analysis scripts
def load_enriched_layer(*args, **kwargs) -> gpd.GeoDataFrame:
    """
    Alias for load_layer_with_demographics.
    
    Provided for convenience and clarity in analysis scripts.
    """
    return load_layer_with_demographics(*args, **kwargs)


if __name__ == '__main__':
    # Simple CLI for testing
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Load LA geography layers with optional demographics"
    )
    parser.add_argument('layer', help='Layer name (e.g., lapd_divisions)')
    parser.add_argument('--with-demographics', action='store_true',
                       help='Load with demographics joined')
    parser.add_argument('--data-dir', default='data/standard',
                       help='Data directory (default: data/standard)')
    parser.add_argument('--base-url', 
                       help='Base URL for remote loading (e.g., https://stilesdata.com/la-geography)')
    parser.add_argument('--info', action='store_true',
                       help='Print layer info and exit')
    
    args = parser.parse_args()
    
    # Load layer
    if args.with_demographics:
        gdf = load_layer_with_demographics(args.layer, 
                                          data_dir=args.data_dir,
                                          base_url=args.base_url)
        print(f"Loaded {args.layer} with demographics")
    else:
        gdf = load_layer(args.layer, 
                        data_dir=args.data_dir,
                        base_url=args.base_url)
        print(f"Loaded {args.layer} (boundaries only)")
    
    if args.info:
        print(f"\nShape: {gdf.shape}")
        print(f"CRS: {gdf.crs}")
        print(f"Columns: {list(gdf.columns)}")
        print(f"\nFirst few rows:")
        print(gdf.head())

