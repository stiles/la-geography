#!/usr/bin/env python3
"""
Test Lambda handler with new airport and election precinct layers.

Simulates Lambda invocations with test coordinates.
"""

import sys
import json
from pathlib import Path

# Add lambda/lookup to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lambda" / "lookup"))

# Override BASE_URL to use local files
import config
config.BASE_URL = f"file://{Path(__file__).parent.parent}/data/standard"

from handler import lambda_handler, _layer_cache


def test_lax_area():
    """Test LAX area (should be in noise contour and election precinct)."""
    print("\n" + "=" * 60)
    print("Testing: LAX Area")
    print("=" * 60)
    
    event = {
        "queryStringParameters": {
            "lat": "33.9416",
            "lon": "-118.4085"
        }
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200, f"Expected 200, got {response['statusCode']}"
    
    body = json.loads(response["body"])
    assert body["status"] == "success", f"Expected success, got {body['status']}"
    
    results = body["results"]
    
    # Check election precinct
    assert results.get("election_precinct"), "Missing election_precinct"
    print(f"  ✓ Election precinct: {results['election_precinct']}")
    
    # Check airport noise
    if results.get("airport_noise"):
        noise = results["airport_noise"]
        if isinstance(noise, dict):
            print(f"  ✓ Airport noise: {noise.get('name')} - {noise.get('class')} dB")
        else:
            print(f"  ✓ Airport noise: {noise}")
    else:
        print(f"  ⚠ Not in airport noise contour")
    
    # Check neighborhood
    if results.get("neighborhood"):
        print(f"  ✓ Neighborhood: {results['neighborhood']}")
    
    return True


def test_downtown_la():
    """Test Downtown LA (should be in precinct but not noise contour)."""
    print("\n" + "=" * 60)
    print("Testing: Downtown LA")
    print("=" * 60)
    
    event = {
        "queryStringParameters": {
            "lat": "34.0522",
            "lon": "-118.2437"
        }
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200, f"Expected 200, got {response['statusCode']}"
    
    body = json.loads(response["body"])
    assert body["status"] == "success", f"Expected success, got {body['status']}"
    
    results = body["results"]
    
    # Check election precinct
    assert results.get("election_precinct"), "Missing election_precinct"
    print(f"  ✓ Election precinct: {results['election_precinct']}")
    
    # Check airport noise (should be None)
    if results.get("airport_noise"):
        print(f"  ⚠ Unexpectedly in airport noise contour: {results['airport_noise']}")
    else:
        print(f"  ✓ Not in airport noise contour (as expected)")
    
    # Check other fields
    if results.get("neighborhood"):
        print(f"  ✓ Neighborhood: {results['neighborhood']}")
    if results.get("lapd_division"):
        print(f"  ✓ LAPD Division: {results['lapd_division']}")
    
    return True


def test_burbank_airport():
    """Test Burbank Airport area (should be in noise contour)."""
    print("\n" + "=" * 60)
    print("Testing: Burbank Airport Area")
    print("=" * 60)
    
    event = {
        "queryStringParameters": {
            "lat": "34.2008",
            "lon": "-118.3585"
        }
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200, f"Expected 200, got {response['statusCode']}"
    
    body = json.loads(response["body"])
    assert body["status"] == "success", f"Expected success, got {body['status']}"
    
    results = body["results"]
    
    # Check election precinct
    assert results.get("election_precinct"), "Missing election_precinct"
    print(f"  ✓ Election precinct: {results['election_precinct']}")
    
    # Check airport noise
    if results.get("airport_noise"):
        noise = results["airport_noise"]
        if isinstance(noise, dict):
            print(f"  ✓ Airport noise: {noise.get('name')} - {noise.get('class')} dB")
        else:
            print(f"  ✓ Airport noise: {noise}")
    else:
        print(f"  ⚠ Not in airport noise contour")
    
    return True


def print_full_response():
    """Print a full response for inspection."""
    print("\n" + "=" * 60)
    print("Full Response Example (LAX Area)")
    print("=" * 60)
    
    event = {
        "queryStringParameters": {
            "lat": "33.9416",
            "lon": "-118.4085"
        }
    }
    
    response = lambda_handler(event, None)
    body = json.loads(response["body"])
    
    print(json.dumps(body, indent=2))


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Lambda Handler with New Layers")
    print("=" * 60)
    print("\nNote: Using local files instead of S3")
    
    try:
        # Clear cache to force reload
        _layer_cache.clear()
        
        test_lax_area()
        test_downtown_la()
        test_burbank_airport()
        print_full_response()
        
        print("\n" + "=" * 60)
        print("✓ ALL LAMBDA TESTS PASSED")
        print("=" * 60)
        return 0
    
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

