"""
AWS Lambda handler for LA Geography point-lookup API (Simplified version).

Uses shapely + requests + json (no GeoPandas/GDAL needed).
Loads GeoJSON from HTTPS and performs point-in-polygon queries.
"""

import json
import logging
from typing import Dict, Any, Optional
import urllib.request

from shapely.geometry import Point, shape
from shapely.strtree import STRtree

from config import LAYERS, BASE_URL, LA_COUNTY_BBOX, DEMOGRAPHICS_LAYERS

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global cache for loaded GeoJSON features
_layer_cache = {}

# Global cache for demographics (keyed by layer_name -> {id -> demographics})
_demographics_cache = {}

# LAPD Division to Bureau mapping (fallback when spatial query fails)
LAPD_DIVISION_TO_BUREAU = {
    # Central Bureau
    "Central": "Central Bureau",
    "Rampart": "Central Bureau",
    "Newton": "Central Bureau",
    "Northeast": "Central Bureau",
    "Hollenbeck": "Central Bureau",
    
    # West Bureau
    "Pacific": "West Bureau",
    "West LA": "West Bureau",
    "West Los Angeles": "West Bureau",
    "West Traffic": "West Bureau",
    "Hollywood": "West Bureau",
    "Wilshire": "West Bureau",
    "Olympic": "West Bureau",
    
    # Valley Bureau
    "Foothill": "Valley Bureau",
    "Devonshire": "Valley Bureau",
    "North Hollywood": "Valley Bureau",
    "Van Nuys": "Valley Bureau",
    "West Valley": "Valley Bureau",
    "Topanga": "Valley Bureau",
    
    # South Bureau
    "77th Street": "South Bureau",
    "Southwest": "South Bureau",
    "Harbor": "South Bureau",
    "Southeast": "South Bureau",
}


def load_geojson_from_url(url: str) -> Dict:
    """Load GeoJSON from HTTPS URL."""
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode('utf-8'))


def load_demographics():
    """
    Load demographics for configured layers from JSON files.
    
    Loads JSON dictionaries that are already keyed by ID field for fast lookups.
    No pandas required!
    """
    global _demographics_cache
    
    for demo_config in DEMOGRAPHICS_LAYERS:
        layer_name = demo_config["name"]
        
        # Skip if already loaded
        if layer_name in _demographics_cache:
            continue
        
        json_url = f"{BASE_URL}/{demo_config['json_file']}"
        
        try:
            logger.info(f"Loading demographics: {layer_name} from {json_url}")
            demographics_dict = load_geojson_from_url(json_url)  # Reuse existing JSON loader
            
            _demographics_cache[layer_name] = demographics_dict
            logger.info(f"Loaded demographics for {len(demographics_dict)} features in {layer_name}")
            
        except Exception as e:
            logger.error(f"Failed to load demographics for {layer_name}: {str(e)}")
            _demographics_cache[layer_name] = None


def load_layers():
    """
    Load all configured layers from S3.
    
    Uses global cache to persist data across warm Lambda invocations.
    Converts GeoJSON features to Shapely geometries for spatial queries.
    Builds spatial indexes (STRtree) for fast point-in-polygon lookups.
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
            geojson_data = load_geojson_from_url(geojson_url)
            
            # Convert features to shapely geometries with properties
            features = []
            geometries = []
            for feature in geojson_data.get('features', []):
                geom = shape(feature['geometry'])
                features.append({
                    'geometry': geom,
                    'properties': feature.get('properties', {})
                })
                geometries.append(geom)
            
            # Build spatial index for fast lookups (O(log n) instead of O(n))
            spatial_index = STRtree(geometries) if geometries else None
            
            _layer_cache[layer_name] = {
                "features": features,
                "spatial_index": spatial_index,
                "config": layer_config
            }
            logger.info(f"Loaded {len(features)} features for {layer_name}")
            
        except Exception as e:
            logger.error(f"Failed to load layer {layer_name}: {str(e)}")
            _layer_cache[layer_name] = {
                "features": None,
                "spatial_index": None,
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
    
    return None


def normalize_text(text: str) -> str:
    """
    Normalize text formatting for consistent output.
    
    Converts ALL CAPS to Title Case, preserves existing title case.
    """
    if not text:
        return text
    
    # Check if text is all caps (more than half uppercase)
    if sum(1 for c in text if c.isupper()) > len(text) * 0.5:
        # Convert to title case, but preserve common abbreviations
        words = text.split()
        normalized_words = []
        
        # Common acronyms to keep uppercase
        ACRONYMS = {'NC', 'USD', 'LAPD', 'LAFD', 'CC'}
        
        for word in words:
            # Keep specific acronyms uppercase
            if word in ACRONYMS:
                normalized_words.append(word)
            # Otherwise convert to title case
            else:
                normalized_words.append(word.title())
        
        return ' '.join(normalized_words)
    
    # Already has mixed case, return as-is
    return text


def query_point(lat: float, lon: float) -> Dict[str, Any]:
    """
    Query all layers for features containing the given point.
    
    Returns a dict mapping response keys to feature names.
    Also includes matched feature IDs for demographics lookup.
    """
    point = Point(lon, lat)  # Shapely uses (lon, lat) order
    results = {}
    matched_ids = {}  # Track IDs for demographics lookup
    matched_features = {}  # Store full feature properties for post-processing
    
    for layer_name, layer_data in _layer_cache.items():
        features = layer_data.get("features")
        spatial_index = layer_data.get("spatial_index")
        config = layer_data["config"]
        response_key = config["response_key"]
        
        # Skip if layer failed to load
        if features is None:
            results[response_key] = None
            continue
        
        try:
            # Use spatial index for fast lookup if available
            if spatial_index:
                # Query spatial index for intersections (O(log n))
                possible_matches_idx = spatial_index.query(point)
                # Filter to actual containment
                matches = [features[i] for i in possible_matches_idx if features[i]['geometry'].contains(point)]
            else:
                # Fallback to linear search (O(n))
                matches = [f for f in features if f['geometry'].contains(point)]
            
            if matches:
                # Take first match (should usually be only one)
                feature = matches[0]
                name_field = config["name_field"]
                id_field = config.get("id_field")
                
                # Store ID for demographics lookup
                if id_field:
                    matched_ids[layer_name] = feature['properties'].get(id_field)
                
                # Store feature properties for governance/type extraction
                matched_features[layer_name] = feature['properties']
                
                # Get the name value from properties
                name_value = feature['properties'].get(name_field)
                
                # Check if layer config specifies extra fields to include
                extra_fields = config.get("extra_fields", [])
                
                if extra_fields:
                    # Build a dict with name and extra fields
                    result_dict = {}
                    if name_value is not None:
                        result_dict["name"] = normalize_text(str(name_value))
                    else:
                        result_dict["name"] = None
                    
                    # Add extra fields
                    for field in extra_fields:
                        field_value = feature['properties'].get(field)
                        if field_value is not None:
                            result_dict[field] = str(field_value)
                        else:
                            result_dict[field] = None
                    
                    results[response_key] = result_dict
                else:
                    # Convert to string and normalize (simple string response)
                    if name_value is not None:
                        results[response_key] = normalize_text(str(name_value))
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
    
    # Post-process results for better null handling
    results = improve_null_values(results)
    
    # Add governance/type context from neighborhood properties
    results = add_governance_context(results, matched_features)
    
    # Add demographics if available
    results = add_demographics(results, matched_ids)
    
    # Add nested service structures (law_enforcement, fire, representation)
    results = add_service_structures(results)
    
    return results


def add_governance_context(results: Dict[str, Any], matched_features: Dict[str, Dict]) -> Dict[str, Any]:
    """
    Add governance/type context from neighborhood and city layers.
    
    Helps frontend distinguish between:
    - Neighborhoods in City of LA (e.g., "Beverly Grove")
    - Standalone cities (e.g., "Pasadena")
    - Unincorporated areas (e.g., "Marina del Rey")
    
    Args:
        results: Current query results
        matched_features: Dict mapping layer_name to feature properties
    
    Returns:
        Results dict with governance context added
    """
    # Extract from neighborhoods layer
    if "la_neighborhoods_comprehensive" in matched_features:
        props = matched_features["la_neighborhoods_comprehensive"]
        
        n_type = props.get('type')  # 'segment-of-a-city', 'standalone-city', 'unincorporated-area'
        n_city = props.get('city')  # 'los-angeles', other city slug, or None
        
        results['neighborhood_type'] = n_type
        results['neighborhood_city_slug'] = n_city
        
        # Derive place category for frontend rendering
        if n_type == 'segment-of-a-city' and n_city == 'los-angeles':
            results['place_category'] = 'la_city_neighborhood'
        elif n_type == 'standalone-city':
            results['place_category'] = 'standalone_city'
        elif n_type == 'unincorporated-area':
            results['place_category'] = 'unincorporated_area'
        else:
            results['place_category'] = None
    
    # Extract from cities layer
    if "la_county_cities" in matched_features:
        city_props = matched_features["la_county_cities"]
        
        # Check if city is incorporated (most cities will be, except "Unincorporated" areas)
        city_name = city_props.get('city_name', '')
        city_type = city_props.get('city_type', '')
        
        # city_type is typically 'City' or 'Unincorporated'
        results['city_is_incorporated'] = (city_type == 'City' and city_name != 'Unincorporated')
    
    return results


def add_service_structures(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add nested service structures for better UX.
    
    Creates law_enforcement, fire, and representation objects from flat fields
    while keeping the flat fields for backwards compatibility.
    
    Args:
        results: Query results with flat fields
    
    Returns:
        Results with nested service structures added
    """
    # Helper to check if value has actual data
    def is_real_value(val):
        return val is not None
    
    # LAW ENFORCEMENT
    law_enforcement = {}
    
    lapd_div = results.get('lapd_division')
    lasd_info = results.get('lasd_station')
    
    if is_real_value(lapd_div):
        # LAPD jurisdiction (City of LA)
        law_enforcement['agency'] = 'LAPD'
        law_enforcement['division'] = lapd_div
        law_enforcement['bureau'] = results.get('lapd_bureau')
    elif is_real_value(lasd_info):
        # Sheriff or municipal police
        if isinstance(lasd_info, dict):
            # We have extra fields (s_type)
            station_name = lasd_info.get('name')
            station_type = lasd_info.get('s_type', '')
            
            if station_type == 'Sheriff':
                law_enforcement['agency'] = 'LA County Sheriff'
                law_enforcement['station'] = station_name
            elif station_type == 'Police':
                # Municipal police department
                law_enforcement['agency'] = f"{station_name} Police Department"
                law_enforcement['station'] = station_name
                law_enforcement['type'] = 'municipal'
            else:
                law_enforcement['agency'] = 'Other'
                law_enforcement['station'] = station_name
        else:
            # Simple string (fallback)
            law_enforcement['agency'] = 'LA County Sheriff'
            law_enforcement['station'] = lasd_info
    else:
        law_enforcement['agency'] = None
        law_enforcement['station'] = None
    
    results['law_enforcement'] = law_enforcement
    
    # FIRE
    fire = {}
    
    lafd_info = results.get('lafd_station')
    lacofd_info = results.get('lacofd_station')
    city_name = results.get('city', '')
    place_category = results.get('place_category')
    
    # Check for placeholder values that indicate bad/missing data
    is_lafd_placeholder = isinstance(lafd_info, str) and lafd_info in ['LA County', 'Other']
    
    # Priority order for determining fire agency:
    # 1. LA County Fire station number (strongest signal - includes contract cities)
    # 2. LAFD with valid data (City of LA)
    # 3. Municipal fire (standalone cities with no county contract)
    
    if is_real_value(lacofd_info):
        # LA County Fire (unincorporated areas OR contract cities like Inglewood)
        # Many cities contract with LA County Fire for service
        fire['agency'] = 'LA County Fire'
        fire['station'] = lacofd_info
        
        # Note if this is a contract city vs unincorporated
        if place_category == 'standalone_city':
            fire['type'] = 'contract'
        elif place_category == 'unincorporated_area':
            fire['type'] = 'direct'
            
    elif is_real_value(lafd_info) and not is_lafd_placeholder:
        # Check if this looks like real LAFD data or municipal FD
        # If station name matches city name for a standalone city, it's likely municipal
        station_matches_city = isinstance(lafd_info, str) and lafd_info.lower() == city_name.lower()
        
        if station_matches_city and place_category == 'standalone_city':
            # Station name matches city = municipal fire department
            # E.g., "Santa Monica" station in Santa Monica = Santa Monica FD
            fire['agency'] = f"{city_name} Fire Department"
            fire['station'] = None
            fire['type'] = 'municipal'
        else:
            # Real LAFD jurisdiction (City of LA)
            fire['agency'] = 'LAFD'
            fire['station'] = lafd_info
            
    else:
        # No data available
        fire['agency'] = None
        fire['station'] = None
    
    results['fire'] = fire
    
    # REPRESENTATION
    representation = {}
    
    council_info = results.get('council_district')
    supervisor_info = results.get('supervisor_district')
    
    if is_real_value(council_info):
        # LA City Council
        district_str = council_info
        
        # Parse district number and name if formatted like "5 - Katy Yaroslavsky"
        if isinstance(district_str, str) and ' - ' in district_str:
            parts = district_str.split(' - ', 1)
            representation['type'] = 'city_council'
            representation['district'] = parts[0].replace('District ', '').strip()
            representation['representative'] = parts[1].strip()
        else:
            representation['type'] = 'city_council'
            representation['district'] = str(district_str).replace('District ', '').strip()
            representation['representative'] = None
    elif is_real_value(supervisor_info):
        # LA County Supervisor
        district_str = supervisor_info
        
        # Parse district number (format: "District 3")
        if isinstance(district_str, str):
            representation['type'] = 'county_supervisor'
            representation['district'] = district_str.replace('District ', '').strip()
            representation['representative'] = None  # Could add supervisor names later
        else:
            representation['type'] = 'county_supervisor'
            representation['district'] = str(district_str)
            representation['representative'] = None
    else:
        # Outside both jurisdictions or unknown
        representation['type'] = 'other'
        representation['district'] = None
        representation['representative'] = None
    
    results['representation'] = representation
    
    return results


def add_demographics(results: Dict[str, Any], matched_ids: Dict[str, str]) -> Dict[str, Any]:
    """
    Add demographic information to results based on matched feature IDs.
    
    Args:
        results: Current query results
        matched_ids: Dict mapping layer_name to matched feature ID
    
    Returns:
        Results dict with demographics added
    """
    if not _demographics_cache:
        return results
    
    # Add neighborhood demographics
    if "la_neighborhoods_comprehensive" in matched_ids and "la_neighborhoods_comprehensive" in _demographics_cache:
        neighborhood_id = matched_ids["la_neighborhoods_comprehensive"]
        demo_dict = _demographics_cache["la_neighborhoods_comprehensive"]
        
        if neighborhood_id in demo_dict:
            results["neighborhood_demographics"] = demo_dict[neighborhood_id]
    
    # Add city demographics
    if "la_county_cities" in matched_ids and "la_county_cities" in _demographics_cache:
        city_id = matched_ids["la_county_cities"]
        demo_dict = _demographics_cache["la_county_cities"]
        
        if city_id in demo_dict:
            results["city_demographics"] = demo_dict[city_id]
    
    return results


def improve_null_values(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Improve data quality where possible (e.g., fill in missing bureau from division).
    
    Note: This used to add "N/A" messages but now leaves nulls as null.
    The nested service structures (law_enforcement, fire, representation) provide
    all the context needed for frontends.
    """
    # If have LAPD division but no bureau, use mapping as fallback
    if results.get('lapd_division') and not results.get('lapd_bureau'):
        # Try to map division to bureau
        division_name = results['lapd_division']
        bureau = LAPD_DIVISION_TO_BUREAU.get(division_name)
        if bureau:
            results['lapd_bureau'] = bureau
            logger.info(f"Mapped division '{division_name}' to bureau '{bureau}' using fallback")
        else:
            logger.warning(f"No bureau mapping found for division: {division_name}")
    
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
        # Handle warm-up pings (just return success, keeps Lambda warm)
        if event.get("warmup"):
            logger.info("Warm-up ping received")
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                },
                "body": json.dumps({"status": "warm"})
            }
        
        # Load layers on first invocation (or if cache is empty)
        if not _layer_cache:
            logger.info("Cold start: loading layers...")
            load_layers()
            logger.info(f"Loaded {len(_layer_cache)} layers")
        
        # Load demographics on first invocation (or if cache is empty)
        if not _demographics_cache:
            logger.info("Loading demographics...")
            load_demographics()
            logger.info(f"Loaded demographics for {len(_demographics_cache)} layers")
        
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
                    "Access-Control-Allow-Origin": "*",
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
                "Access-Control-Allow-Origin": "*",
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

