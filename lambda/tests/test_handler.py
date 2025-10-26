"""
Unit tests for LA Geography point-lookup Lambda handler.

Run with: pytest lambda/tests/
"""

import json
import pytest
from unittest.mock import Mock, patch
import geopandas as gpd
from shapely.geometry import Point, Polygon

# Import handler functions
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lookup'))

from handler import lambda_handler, validate_coordinates, query_point, load_layers
from config import LAYERS


class TestCoordinateValidation:
    """Test coordinate validation logic."""
    
    def test_valid_coordinates(self):
        """Test that valid LA coordinates pass validation."""
        assert validate_coordinates(34.0522, -118.2437) is None
        assert validate_coordinates(33.9850, -118.4695) is None
        assert validate_coordinates(34.1478, -118.1445) is None
    
    def test_invalid_latitude(self):
        """Test that invalid latitudes are rejected."""
        error = validate_coordinates(91.0, -118.2437)
        assert error is not None
        assert "latitude" in error.lower()
        
        error = validate_coordinates(-91.0, -118.2437)
        assert error is not None
        assert "latitude" in error.lower()
    
    def test_invalid_longitude(self):
        """Test that invalid longitudes are rejected."""
        error = validate_coordinates(34.0522, 181.0)
        assert error is not None
        assert "longitude" in error.lower()
        
        error = validate_coordinates(34.0522, -181.0)
        assert error is not None
        assert "longitude" in error.lower()


class TestLambdaHandler:
    """Test Lambda handler function."""
    
    def test_missing_lat_parameter(self):
        """Test error when lat parameter is missing."""
        event = {
            "queryStringParameters": {
                "lon": "-118.2437"
            }
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["status"] == "error"
        assert "lat" in body["message"].lower()
    
    def test_missing_lon_parameter(self):
        """Test error when lon parameter is missing."""
        event = {
            "queryStringParameters": {
                "lat": "34.0522"
            }
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["status"] == "error"
        assert "lon" in body["message"].lower()
    
    def test_missing_query_parameters(self):
        """Test error when queryStringParameters is missing."""
        event = {}
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["status"] == "error"
    
    def test_invalid_coordinate_format(self):
        """Test error when coordinates are not numeric."""
        event = {
            "queryStringParameters": {
                "lat": "not-a-number",
                "lon": "-118.2437"
            }
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["status"] == "error"
        assert "numeric" in body["message"].lower()
    
    def test_invalid_coordinates(self):
        """Test error when coordinates are out of valid range."""
        event = {
            "queryStringParameters": {
                "lat": "95.0",  # Invalid latitude
                "lon": "-118.2437"
            }
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["status"] == "error"
    
    def test_cors_headers(self):
        """Test that CORS headers are present in response."""
        event = {
            "queryStringParameters": {
                "lat": "34.0522",
                "lon": "-118.2437"
            }
        }
        
        # Mock the load_layers and query_point to avoid actual data loading
        with patch('handler._layer_cache', {"mock": {}}):
            with patch('handler.load_layers'):
                with patch('handler.query_point', return_value={}):
                    response = lambda_handler(event, None)
        
        assert "Access-Control-Allow-Origin" in response["headers"]
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"


class TestQueryPoint:
    """Test point-in-polygon query logic."""
    
    @pytest.fixture
    def mock_layer_cache(self):
        """Create mock layer cache with simple test geometries."""
        # Create a simple polygon covering downtown LA area
        downtown_poly = Polygon([
            (-118.27, 34.04),
            (-118.27, 34.06),
            (-118.24, 34.06),
            (-118.24, 34.04),
            (-118.27, 34.04)
        ])
        
        downtown_gdf = gpd.GeoDataFrame(
            {"name": ["Downtown"], "slug": ["downtown"]},
            geometry=[downtown_poly],
            crs="EPSG:4326"
        )
        
        # Create a polygon for Venice
        venice_poly = Polygon([
            (-118.48, 33.98),
            (-118.48, 34.00),
            (-118.45, 34.00),
            (-118.45, 33.98),
            (-118.48, 33.98)
        ])
        
        venice_gdf = gpd.GeoDataFrame(
            {"name": ["Venice"], "slug": ["venice"]},
            geometry=[venice_poly],
            crs="EPSG:4326"
        )
        
        return {
            "la_neighborhoods_comprehensive": {
                "gdf": gpd.GeoDataFrame(
                    pd.concat([downtown_gdf, venice_gdf], ignore_index=True)
                ),
                "config": {
                    "name": "la_neighborhoods_comprehensive",
                    "response_key": "neighborhood",
                    "name_field": "name",
                    "id_field": "slug"
                }
            }
        }
    
    def test_point_in_polygon(self, mock_layer_cache):
        """Test finding a point inside a polygon."""
        with patch('handler._layer_cache', mock_layer_cache):
            results = query_point(34.05, -118.25)  # Downtown LA
            assert results["neighborhood"] == "Downtown"
    
    def test_point_outside_all_polygons(self, mock_layer_cache):
        """Test point that doesn't intersect any polygons."""
        with patch('handler._layer_cache', mock_layer_cache):
            results = query_point(35.0, -120.0)  # Far outside
            assert results["neighborhood"] is None


class TestKnownLocations:
    """
    Integration tests for known LA locations.
    
    These tests require actual data files and will be skipped if run
    without network access to S3.
    """
    
    # Known test coordinates with expected results
    TEST_LOCATIONS = [
        {
            "name": "Downtown LA (City Hall)",
            "lat": 34.0537,
            "lon": -118.2427,
            "expected": {
                "neighborhood": "Downtown",
                "city": "Los Angeles",
                "lapd_division": "Central",
            }
        },
        {
            "name": "Venice Beach",
            "lat": 33.9850,
            "lon": -118.4695,
            "expected": {
                "neighborhood": "Venice",
                "city": "Los Angeles",
                "lapd_division": "Pacific",
            }
        },
        {
            "name": "Pasadena (City Hall)",
            "lat": 34.1478,
            "lon": -118.1445,
            "expected": {
                "neighborhood": "Pasadena",
                "city": "Pasadena",
                "lapd_division": None,  # Outside LAPD jurisdiction
            }
        },
    ]
    
    @pytest.mark.integration
    @pytest.mark.parametrize("location", TEST_LOCATIONS)
    def test_known_location(self, location):
        """
        Test lookup for known locations.
        
        This is an integration test that requires loading actual data from S3.
        Run with: pytest -m integration
        """
        event = {
            "queryStringParameters": {
                "lat": str(location["lat"]),
                "lon": str(location["lon"])
            }
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 200, f"Failed for {location['name']}"
        
        body = json.loads(response["body"])
        assert body["status"] == "success"
        
        results = body["results"]
        
        # Check expected values
        for key, expected_value in location["expected"].items():
            assert key in results, f"Missing key '{key}' for {location['name']}"
            if expected_value is not None:
                assert results[key] == expected_value, \
                    f"Wrong {key} for {location['name']}: got {results[key]}, expected {expected_value}"


# Import pandas for DataFrame operations
import pandas as pd


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])

