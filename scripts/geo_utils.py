"""
Shared utilities for la-geo pipeline.

Provides common functions for CRS transformations, area calculations,
field normalization, and data validation.
"""

import geopandas as gpd
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


def load_config(config_path: str = "config/layers.yml") -> Dict:
    """Load layer configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def area_sqmi(gdf: gpd.GeoDataFrame) -> gpd.GeoSeries:
    """
    Calculate area in square miles using California Albers (EPSG:3310).
    
    This avoids Web Mercator distortion and provides accurate area measurements
    for the LA region.
    
    Args:
        gdf: GeoDataFrame in any CRS (will be reprojected to 3310)
    
    Returns:
        Series with area in square miles
    """
    # Project to California Albers (meters)
    gdf_albers = gdf.to_crs(3310)
    
    # Convert m² to mi² (1 mi² = 2,589,988.110336 m²)
    return gdf_albers.geometry.area / 2_589_988.110336


def ensure_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Ensure GeoDataFrame is in WGS84 (EPSG:4326).
    
    Args:
        gdf: GeoDataFrame in any CRS
    
    Returns:
        GeoDataFrame in EPSG:4326
    """
    if gdf.crs is None:
        print("  ⚠ No CRS specified, assuming EPSG:4326")
        gdf = gdf.set_crs(4326)
    elif gdf.crs.to_epsg() != 4326:
        print(f"  Reprojecting from {gdf.crs} to EPSG:4326")
        gdf = gdf.to_crs(4326)
    return gdf


def normalize_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Normalize column names to lower_snake_case.
    
    Args:
        gdf: GeoDataFrame with any column naming convention
    
    Returns:
        GeoDataFrame with normalized column names
    """
    gdf.columns = gdf.columns.str.lower().str.strip().str.replace(' ', '_')
    return gdf


def add_area_if_polygon(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Add area_sqmi column if GeoDataFrame contains polygons.
    
    Args:
        gdf: GeoDataFrame with any geometry type
    
    Returns:
        GeoDataFrame with area_sqmi column added (if applicable)
    """
    geom_types = gdf.geometry.geom_type.unique()
    
    if any(gt in ['Polygon', 'MultiPolygon'] for gt in geom_types):
        gdf['area_sqmi'] = area_sqmi(gdf)
        print(f"  ✓ Calculated area (min: {gdf['area_sqmi'].min():.2f}, "
              f"max: {gdf['area_sqmi'].max():.2f} sq mi)")
    
    return gdf


def add_metadata(gdf: gpd.GeoDataFrame, source_url: str) -> gpd.GeoDataFrame:
    """
    Add metadata fields to GeoDataFrame.
    
    Args:
        gdf: GeoDataFrame
        source_url: Source REST endpoint URL
    
    Returns:
        GeoDataFrame with metadata fields added
    """
    gdf['source_url'] = source_url
    gdf['fetched_at'] = datetime.now().isoformat()
    return gdf


def validate_bbox(gdf: gpd.GeoDataFrame) -> bool:
    """
    Check if GeoDataFrame bounds are within LA County extent.
    
    Rough LA County bounds in WGS84:
    - Longitude: -119.1 to -116.9
    - Latitude: 33.3 to 35.0
    
    Args:
        gdf: GeoDataFrame in EPSG:4326
    
    Returns:
        True if bounds are reasonable for LA County
    """
    minx, miny, maxx, maxy = gdf.total_bounds
    
    lon_ok = (-119.5 < minx < -116.5) and (-119.5 < maxx < -116.5)
    lat_ok = (33.0 < miny < 35.5) and (33.0 < maxy < 35.5)
    
    if not (lon_ok and lat_ok):
        print(f"  ⚠ Bounds check failed: ({minx:.2f}, {miny:.2f}, {maxx:.2f}, {maxy:.2f})")
        return False
    
    return True


def fix_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Attempt to fix invalid geometries using buffer(0).
    
    Args:
        gdf: GeoDataFrame with potentially invalid geometries
    
    Returns:
        GeoDataFrame with fixed geometries
    """
    invalid_count = (~gdf.geometry.is_valid).sum()
    
    if invalid_count > 0:
        print(f"  ⚠ Found {invalid_count} invalid geometries, attempting to fix...")
        gdf['geometry'] = gdf.geometry.buffer(0)
        
        still_invalid = (~gdf.geometry.is_valid).sum()
        if still_invalid > 0:
            print(f"  ⚠ Still have {still_invalid} invalid geometries after fix")
        else:
            print(f"  ✓ Fixed all invalid geometries")
    
    return gdf


def get_bbox_string(gdf: gpd.GeoDataFrame) -> str:
    """
    Get bounding box as string for quick sanity checks.
    
    Args:
        gdf: GeoDataFrame in any CRS
    
    Returns:
        Comma-separated bbox string: "minx,miny,maxx,maxy"
    """
    minx, miny, maxx, maxy = gdf.total_bounds
    return f"{minx:.6f},{miny:.6f},{maxx:.6f},{maxy:.6f}"


def clip_to_boundary(
    gdf: gpd.GeoDataFrame,
    boundary: gpd.GeoDataFrame,
    buffer_mi: float = 0.0
) -> gpd.GeoDataFrame:
    """
    Clip a GeoDataFrame to a boundary (e.g., clip freeways to LA County).
    
    Args:
        gdf: GeoDataFrame to clip
        boundary: Boundary GeoDataFrame to clip to
        buffer_mi: Optional buffer in miles to add to boundary
    
    Returns:
        Clipped GeoDataFrame
    """
    # Ensure same CRS
    if gdf.crs != boundary.crs:
        boundary = boundary.to_crs(gdf.crs)
    
    # Apply buffer if requested (convert miles to degrees ~0.0145 deg/mi)
    if buffer_mi > 0:
        boundary = boundary.copy()
        boundary['geometry'] = boundary.geometry.buffer(buffer_mi * 0.0145)
    
    # Clip
    clipped = gpd.clip(gdf, boundary)
    print(f"  Clipped from {len(gdf)} to {len(clipped)} features")
    
    return clipped

