"""
AWS Lambda handler for LA Geography point-lookup API.

Performs point-in-polygon queries to determine which geographic features
contain a given lat/lon coordinate.
"""

import json
import logging
from typing import Dict, Any, Optional
from urllib.parse import parse_qs

import geopandas as gpd
from shapely.geometry import Point

from config import LAYERS, BASE_URL, LA_COUNTY_BBOX

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global cache for loaded GeoDataFrames (persists across warm Lambda invocations)
_layer_cache = {}


def load_layers():
    """
    Load all configured layers from S3.
    
    Uses global cache to persist data across warm Lambda invocations.
    Only loads layers that haven't been loaded yet.
    """
    global _layer_cache
    
    for layer_config in LAYERS:
        layer_name = layer_config["name"]
        
        # Skip if already loaded
        if layer_name in _layer_cache:
            continue
            
        geojson_url = f"{BASE_URL}/{layer_config['geojson_file']}"
        
        try:
            logger.info(f"Loading layer: {layer_name} from {geojson_url}")
            gdf = gpd.read_file(geojson_url)
            
            # Ensure WGS84 (EPSG:4326)
            if gdf.crs is None or gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs(4326)
            
            _layer_cache[layer_name] = {
                "gdf": gdf,
                "config": layer_config
            }
            logger.info(f"Loaded {len(gdf)} features for {layer_name}")
            
        except Exception as e:
            logger.error(f"Failed to load layer {layer_name}: {str(e)}")
            # Continue loading other layers even if one fails
            _layer_cache[layer_name] = {
                "gdf": None,
                "config": layer_config,
                "error": str(e)
            }


def validate_coordinates(lat: float, lon: float) -> Optional[str]:
    """
    Validate that coordinates are valid and roughly within LA County.
    
    Returns error message if invalid, None if valid.
    """
    # Check basic validity
    if not (-90 <= lat <= 90):
        return f"Invalid latitude: {lat}. Must be between -90 and 90."
    
    if not (-180 <= lon <= 180):
        return f"Invalid longitude: {lon}. Must be between -180 and 180."
    
    # Check if roughly within LA County bounds (loose check)
    bbox = LA_COUNTY_BBOX
    if not (bbox["min_lat"] <= lat <= bbox["max_lat"] and 
            bbox["min_lon"] <= lon <= bbox["max_lon"]):
        logger.warning(f"Coordinates ({lat}, {lon}) outside LA County bounds")
        # Don't error, just log - might be edge case or intentional
    
    return None


def query_point(lat: float, lon: float) -> Dict[str, Any]:
    """
    Query all layers for features containing the given point.
    
    Returns a dict mapping response keys to feature names.
    """
    point = Point(lon, lat)  # Shapely uses (lon, lat) order
    results = {}
    
    for layer_name, layer_data in _layer_cache.items():
        gdf = layer_data.get("gdf")
        config = layer_data["config"]
        response_key = config["response_key"]
        
        # Skip if layer failed to load
        if gdf is None:
            results[response_key] = None
            continue
        
        try:
            # Find features containing the point
            matches = gdf[gdf.contains(point)]
            
            if len(matches) > 0:
                # Take first match (should usually be only one)
                feature = matches.iloc[0]
                name_field = config["name_field"]
                
                # Get the name value
                name_value = feature.get(name_field)
                
                # Convert to Python native type (handles numpy types)
                if name_value is not None:
                    results[response_key] = str(name_value)
                else:
                    results[response_key] = None
                    
                if len(matches) > 1:
                    logger.warning(
                        f"Multiple matches found for {layer_name} at ({lat}, {lon}). "
                        f"Using first match: {results[response_key]}"
                    )
            else:
                results[response_key] = None
                
        except Exception as e:
            logger.error(f"Error querying {layer_name}: {str(e)}")
            results[response_key] = None
    
    return results


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for point-lookup API.
    
    Expected event structure (from API Gateway):
    {
        "queryStringParameters": {
            "lat": "34.0522",
            "lon": "-118.2437"
        }
    }
    """
    try:
        # Load layers on first invocation (or if cache is empty)
        if not _layer_cache:
            logger.info("Cold start: loading layers...")
            load_layers()
            logger.info(f"Loaded {len(_layer_cache)} layers")
        
        # Parse query parameters
        query_params = event.get("queryStringParameters") or {}
        
        # Get lat/lon from query params
        lat_str = query_params.get("lat")
        lon_str = query_params.get("lon")
        
        if not lat_str or not lon_str:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",  # Enable CORS
                },
                "body": json.dumps({
                    "status": "error",
                    "message": "Missing required parameters. Please provide both 'lat' and 'lon'.",
                    "example": "/lookup?lat=34.0522&lon=-118.2437"
                })
            }
        
        # Parse to floats
        try:
            lat = float(lat_str)
            lon = float(lon_str)
        except ValueError:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({
                    "status": "error",
                    "message": f"Invalid coordinate values. lat='{lat_str}', lon='{lon_str}' must be numeric.",
                    "example": "/lookup?lat=34.0522&lon=-118.2437"
                })
            }
        
        # Validate coordinates
        validation_error = validate_coordinates(lat, lon)
        if validation_error:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({
                    "status": "error",
                    "message": validation_error
                })
            }
        
        # Query all layers
        logger.info(f"Querying point: ({lat}, {lon})")
        results = query_point(lat, lon)
        
        # Build response
        response_body = {
            "status": "success",
            "query": {
                "lat": lat,
                "lon": lon
            },
            "results": results
        }
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",  # Enable CORS
            },
            "body": json.dumps(response_body)
        }
        
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({
                "status": "error",
                "message": "Internal server error. Please try again later."
            })
        }

