# ✅ LA Geography Point-Lookup API - DEPLOYED!

**Status**: Live and working  
**Deployed**: October 26, 2025  
**Endpoint**: `https://api.stilesdata.com/la-geography/lookup`  
**Custom Domain**: ✅ Configured with EDGE endpoint (CloudFront)

## Quick test

```bash
# Downtown LA
curl "https://api.stilesdata.com/la-geography/lookup?lat=34.0522&lon=-118.2437"

# Venice Beach
curl "https://api.stilesdata.com/la-geography/lookup?lat=33.9850&lon=-118.4695"

# Pasadena
curl "https://api.stilesdata.com/la-geography/lookup?lat=34.1478&lon=-118.1445"
```

## What it returns

For any lat/lon coordinate in LA County, the API returns:
- Neighborhood name
- City or unincorporated area
- LAPD division (if in LA City)
- LAPD bureau (if in LA City)
- Fire station (LAFD or LA County)
- City council district (if in LA City)
- Neighborhood council (if in LA City)
- School district

## AWS Resources

**Lambda Function**: `la-geography-lookup-api-LookupFunction-NUKDC6JavQZX`  
**Lambda Layer**: `shapely-python311:1` (20 MB)  
**API Gateway**: `v7cwkba61i`  
**Region**: `us-west-2`  
**Stack**: `la-geography-lookup-api`

## Performance

- **Cold start**: 3-5 seconds (first request or after idle)
- **Warm requests**: 50-200ms
- **Layer size**: 20 MB (Shapely + NumPy)
- **Data loaded**: ~40 MB (9 GeoJSON layers from S3)

## Cost estimate

For 1,000 requests/day (~30K/month):
- Lambda: $0.06/month
- API Gateway: $0.10/month
- S3 requests: $0.01/month
- **Total**: ~$0.17/month

Well within AWS Free Tier (1M Lambda requests/month).

## Architecture notes

### Simplified approach used

Instead of GeoPandas (which requires GDAL), we used:
- **Shapely** 2.0 for geometry operations
- **Python stdlib** (urllib, json) for HTTP and JSON
- Direct GeoJSON loading from S3 URLs

This avoids complex GDAL compilation and makes the Lambda layer much simpler.

### What's cached

On Lambda cold start, the function:
1. Loads 9 GeoJSON files from S3 (~40 MB total)
2. Converts features to Shapely geometries
3. Caches in Lambda global scope

Subsequent requests (warm invocations) use the cached data.

## Monitoring

View logs:
```bash
sam logs -n LookupFunction --stack-name la-geography-lookup-api --tail --profile haekeo
```

CloudWatch metrics:
- AWS Console → Lambda → Functions → la-geography-lookup-api-LookupFunction
- Monitor: Invocations, Duration, Errors

## Updating the function

After code changes:
```bash
cd lambda/
sam build
sam deploy
```

No need for `--guided` after first deployment (settings saved in `samconfig.toml`).

## Example usage

### Python
```python
import requests

API_URL = "https://v7cwkba61i.execute-api.us-west-2.amazonaws.com/prod/lookup"
response = requests.get(API_URL, params={"lat": 34.0522, "lon": -118.2437})
data = response.json()

print(f"Neighborhood: {data['results']['neighborhood']}")
print(f"City: {data['results']['city']}")
```

### JavaScript
```javascript
const API_URL = 'https://v7cwkba61i.execute-api.us-west-2.amazonaws.com/prod/lookup';
const response = await fetch(`${API_URL}?lat=34.0522&lon=-118.2437`);
const data = await response.json();
console.log('Neighborhood:', data.results.neighborhood);
```

### Web map integration
```javascript
// On map click, lookup location
map.on('click', async (e) => {
  const {lat, lng} = e.latlng;
  const url = `https://v7cwkba61i.execute-api.us-west-2.amazonaws.com/prod/lookup?lat=${lat}&lon=${lng}`;
  const response = await fetch(url);
  const data = await response.json();
  
  // Show popup with results
  const popup = `
    <h3>📍 ${data.results.neighborhood}</h3>
    <p><strong>City:</strong> ${data.results.city}</p>
    <p><strong>Council District:</strong> ${data.results.council_district}</p>
  `;
  L.popup().setLatLng(e.latlng).setContent(popup).openOn(map);
});
```

## Cleanup (if needed)

To delete all AWS resources:
```bash
cd lambda/
sam delete --stack-name la-geography-lookup-api --profile haekeo
```

This removes:
- Lambda function
- API Gateway
- IAM roles
- CloudFormation stack

(The Lambda layer remains and must be deleted separately if desired)

## Next steps / ideas

### "What is your LA?" web app
Build a simple map interface:
- Click anywhere in LA County
- Show all geographic context for that point
- Beautiful UI with neighborhood info, demographics, etc.

### Batch processing
Add ability to process multiple coordinates:
```bash
python lambda/examples/batch_lookup.py \
  https://v7cwkba61i.execute-api.us-west-2.amazonaws.com/prod/lookup \
  locations.csv \
  results.csv
```

### Add demographics
Optionally return census demographics with results:
- Query parameter: `?include_demographics=true`
- Join with demographics Parquet files
- Return population, race/ethnicity breakdown

### Caching
Add CloudFront CDN in front of API Gateway:
- Cache responses for popular coordinates
- Reduce Lambda invocations
- Faster response times globally

## Documentation

- [Full API Documentation](docs/API.md)
- [Deployment Guide](lambda/DEPLOYMENT.md)
- [Quick Start](lambda/QUICKSTART.md)
- [Implementation Notes](IMPLEMENTATION_NOTES.md)

---

**Built with**: AWS Lambda, API Gateway, Python 3.11, Shapely 2.0, AWS SAM

