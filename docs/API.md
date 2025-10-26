# LA geography point-lookup API

**Find what you know about any LA location** - Get neighborhood, city, police division, fire station, and more for any coordinate in Los Angeles County.

## Quick start

**Endpoint**: `https://api.stilesdata.com/la-geography/lookup`

**Example request**:
```bash
curl "https://api.stilesdata.com/la-geography/lookup?lat=34.0522&lon=-118.2437"
```

**Example response**:
```json
{
  "status": "success",
  "query": {
    "lat": 34.0522,
    "lon": -118.2437
  },
  "results": {
    "neighborhood": "Downtown",
    "city": "Los Angeles",
    "lapd_division": "Central",
    "lapd_bureau": "Central Bureau",
    "lafd_station": "Station 3",
    "lacofd_station": null,
    "council_district": "District 14",
    "neighborhood_council": "Downtown Los Angeles Neighborhood Council",
    "school_district": "Los Angeles Unified"
  }
}
```

## API reference

### Endpoint

```
GET /lookup
```

### Query parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lat` | float | Yes | Latitude in decimal degrees (WGS84) |
| `lon` | float | Required | Longitude in decimal degrees (WGS84) |

**Coordinate format**: Decimal degrees in WGS84 (EPSG:4326)
- Latitude range: -90 to 90
- Longitude range: -180 to 180
- LA County typical range: lat 33.7-34.8, lon -119.0 to -117.6

### Response format

#### Success response

**Status code**: `200 OK`

```json
{
  "status": "success",
  "query": {
    "lat": 34.0522,
    "lon": -118.2437
  },
  "results": {
    "neighborhood": "Downtown",
    "city": "Los Angeles",
    "lapd_division": "Central",
    "lapd_bureau": "Central Bureau",
    "lafd_station": "Station 3",
    "lacofd_station": null,
    "council_district": "District 14",
    "neighborhood_council": "Downtown Los Angeles Neighborhood Council",
    "school_district": "Los Angeles Unified"
  }
}
```

#### Results object

Each key in `results` represents a geographic layer. Value is the name of the feature containing the query point, or `null` if the point is not within any feature in that layer.

| Key | Description | Example value |
|-----|-------------|---------------|
| `neighborhood` | LA County neighborhood (comprehensive) | "Downtown", "Venice", "Pasadena" |
| `city` | City or unincorporated area | "Los Angeles", "Santa Monica", "Unincorporated" |
| `lapd_division` | LAPD division (city only) | "Central", "Pacific", null (if outside LAPD) |
| `lapd_bureau` | LAPD bureau (city only) | "Central Bureau", "West Bureau", null |
| `lafd_station` | LA Fire Dept station (city only) | "Station 3", "Station 62", null |
| `lacofd_station` | LA County Fire Dept station | "Station 23", "Station 69", null |
| `council_district` | LA City Council district (city only) | "District 14", "District 11", null |
| `neighborhood_council` | Neighborhood council (city only) | "Downtown LA NC", null |
| `school_district` | School district | "Los Angeles Unified", "Pasadena Unified" |

**Note**: Some values may be `null` if:
- The coordinate is outside that layer's coverage (e.g., LAPD divisions only cover LA City)
- The coordinate falls in a gap between features
- The data layer doesn't have a feature at that location

#### Error responses

**Missing parameters** - `400 Bad Request`
```json
{
  "status": "error",
  "message": "Missing required parameters. Please provide both 'lat' and 'lon'.",
  "example": "/lookup?lat=34.0522&lon=-118.2437"
}
```

**Invalid coordinate format** - `400 Bad Request`
```json
{
  "status": "error",
  "message": "Invalid coordinate values. lat='abc', lon='-118.2437' must be numeric.",
  "example": "/lookup?lat=34.0522&lon=-118.2437"
}
```

**Invalid coordinate range** - `400 Bad Request`
```json
{
  "status": "error",
  "message": "Invalid latitude: 95.0. Must be between -90 and 90."
}
```

**Server error** - `500 Internal Server Error`
```json
{
  "status": "error",
  "message": "Internal server error. Please try again later."
}
```

## Usage examples

### cURL

```bash
# Downtown LA
curl "https://YOUR-API-ID.execute-api.us-west-2.amazonaws.com/prod/lookup?lat=34.0522&lon=-118.2437"

# Venice Beach
curl "https://YOUR-API-ID.execute-api.us-west-2.amazonaws.com/prod/lookup?lat=33.9850&lon=-118.4695"

# Pasadena
curl "https://YOUR-API-ID.execute-api.us-west-2.amazonaws.com/prod/lookup?lat=34.1478&lon=-118.1445"
```

### Python

```python
import requests

API_ENDPOINT = "https://YOUR-API-ID.execute-api.us-west-2.amazonaws.com/prod/lookup"

def lookup_location(lat, lon):
    """Look up geographic information for a coordinate."""
    response = requests.get(API_ENDPOINT, params={"lat": lat, "lon": lon})
    response.raise_for_status()
    return response.json()

# Example usage
result = lookup_location(34.0522, -118.2437)
print(f"Neighborhood: {result['results']['neighborhood']}")
print(f"City: {result['results']['city']}")
print(f"LAPD Division: {result['results']['lapd_division']}")
```

### JavaScript

```javascript
// Browser or Node.js with fetch
async function lookupLocation(lat, lon) {
  const endpoint = 'https://YOUR-API-ID.execute-api.us-west-2.amazonaws.com/prod/lookup';
  const url = `${endpoint}?lat=${lat}&lon=${lon}`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  
  return await response.json();
}

// Example usage
lookupLocation(34.0522, -118.2437)
  .then(data => {
    console.log('Neighborhood:', data.results.neighborhood);
    console.log('City:', data.results.city);
    console.log('LAPD Division:', data.results.lapd_division);
  });
```

### R

```r
library(httr)
library(jsonlite)

lookup_location <- function(lat, lon) {
  endpoint <- "https://YOUR-API-ID.execute-api.us-west-2.amazonaws.com/prod/lookup"
  
  response <- GET(endpoint, query = list(lat = lat, lon = lon))
  stop_for_status(response)
  
  content(response, "text") %>% fromJSON()
}

# Example usage
result <- lookup_location(34.0522, -118.2437)
cat("Neighborhood:", result$results$neighborhood, "\n")
cat("City:", result$results$city, "\n")
cat("LAPD Division:", result$results$lapd_division, "\n")
```

## Performance

- **Cold start**: 3-5 seconds (first request or after idle period)
- **Warm requests**: 50-200ms (typical)
- **Caching**: Layers cached after first request, reused for subsequent requests
- **Rate limits**: None currently (fair use expected)

**Note**: The first request to the API (or first request after ~15 minutes of inactivity) will be slower due to Lambda cold start. Subsequent requests are much faster.

## Data sources

All geographic layers come from official government sources or trusted journalism organizations:

- **LA County neighborhoods**: LA Times Mapping LA project (archived)
- **City boundaries**: LA County Department of Regional Planning
- **LAPD boundaries**: LAPD GIS Mapping
- **Fire stations**: LAFD and LA County Fire Department
- **Council districts**: LA City
- **School districts**: LA County Office of Education

See [main README](../README.md#data-sources) for detailed source information.

## CORS support

The API includes CORS headers to allow cross-origin requests from web applications:
```
Access-Control-Allow-Origin: *
```

This means you can call the API directly from JavaScript in a web browser without proxy servers.

## Cost and rate limits

**Current status**: No authentication required, no rate limits

**Expected costs**: ~$4 per million requests
- Lambda: $0.20/1M requests
- API Gateway: $3.50/1M requests  
- S3 data transfer: $0.40/1M requests

**AWS Free Tier** covers substantial usage:
- Lambda: 1M requests/month free
- API Gateway: 1M requests/month free (first 12 months)

If usage increases significantly, we may add:
- API key requirement (for light rate limiting)
- CloudFront CDN (for caching popular coordinates)
- Usage quotas (fair use)

## Privacy

- **No logging of queries**: Coordinates are not stored or logged (beyond standard AWS CloudWatch logs)
- **No authentication required**: No user tracking or API keys
- **No personal data**: Only coordinates are processed, no user information collected

## Limitations

- **LA County only**: Optimized for Los Angeles County. Coordinates outside LA County may return all null results.
- **Point queries only**: Currently only supports single coordinate lookups. Batch queries not yet supported.
- **No demographics**: Returns geographic identifiers only. For census demographics, see [main data repository](../README.md#census-demographics-enrichment).
- **Static data**: Layers updated periodically, not real-time

## Troubleshooting

### All results are null

- **Cause**: Coordinate is outside all layer boundaries
- **Check**: Is the coordinate within LA County? (lat ~33.7-34.8, lon ~-119.0 to -117.6)
- **Try**: Use a known LA location first (34.0522, -118.2437)

### "Invalid coordinate" error

- **Cause**: Latitude or longitude out of valid range
- **Check**: Latitude must be -90 to 90, longitude must be -180 to 180
- **Note**: Negative longitude for western hemisphere (LA is around -118)

### Slow response time

- **Cause**: Lambda cold start (first request or after idle)
- **Solution**: Subsequent requests will be much faster (<200ms)
- **Normal**: First request may take 3-5 seconds

### 500 Internal Server Error

- **Cause**: Server error (logged to CloudWatch)
- **Try**: Wait a moment and retry
- **Contact**: If persistent, report issue on GitHub

## Future enhancements

Potential additions (not currently available):

- **Batch lookups**: Query multiple coordinates in one request
- **Demographics**: Include census data in response
- **Nearest feature**: Distance to closest police station, fire station, etc.
- **Reverse geocoding**: Convert address → coordinate → lookup
- **Historical data**: Query boundaries from different time periods
- **Custom layers**: User-defined geographic filters

## Support

- **Documentation**: [LA Geography README](../README.md)
- **Data repository**: [GitHub](https://github.com/username/la-geography)
- **Issues**: Report bugs or request features on GitHub

## License

API and data retain their original licenses. See [LICENSE](../LICENSE) and source attributions in [main README](../README.md#data-sources).

