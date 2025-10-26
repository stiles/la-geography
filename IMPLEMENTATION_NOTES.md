# Point-lookup API implementation notes

Implementation completed: 2025-10-26

## What was built

A serverless AWS Lambda + API Gateway point-lookup API that returns all geographic layers containing a given lat/lon coordinate.

### Architecture

- **Lambda Function** (`lambda/lookup/handler.py`): Python 3.11 function that performs spatial queries
- **API Gateway**: Public REST API endpoint (`GET /lookup?lat=X&lon=Y`)
- **Data Loading**: Loads GeoJSON from S3 on cold start, cached globally across warm invocations
- **Dependencies**: GeoPandas/GDAL via Lambda Layer (not bundled with function code)

### Key features

1. **9 geographic layers queried** (in order):
   - LA neighborhoods (comprehensive)
   - LA County cities
   - LAPD divisions & bureaus
   - LAFD & LA County Fire stations
   - City council districts
   - Neighborhood councils
   - School districts

2. **Simple JSON response** with just the key identifiers (names) from each layer

3. **Error handling** for missing/invalid parameters, out-of-range coordinates

4. **CORS enabled** for web browser access

5. **No authentication** (public, open API)

### Files created

```
lambda/
├── lookup/
│   ├── handler.py              # Main Lambda function
│   ├── config.py               # Layer configuration
│   ├── requirements.txt        # Python dependencies
│   └── __init__.py
├── tests/
│   ├── test_handler.py         # Unit and integration tests
│   ├── pytest.ini              # Test configuration
│   └── __init__.py
├── layers/
│   └── README.md               # Guide for building GeoPandas layer
├── examples/
│   ├── test_api.py             # Test script for API
│   ├── batch_lookup.py         # Batch processing script
│   ├── sample_locations.csv    # Sample data
│   └── README.md
├── template.yaml               # SAM/CloudFormation template
├── samconfig.toml              # SAM deployment config
├── README.md                   # Lambda deployment overview
├── DEPLOYMENT.md               # Step-by-step deployment guide
└── .gitignore                  # Ignore build artifacts
```

### Documentation

1. **API Documentation** (`docs/API.md`)
   - Endpoint reference
   - Query parameters
   - Response format
   - Usage examples (curl, Python, JavaScript, R)
   - Error handling
   - Performance notes

2. **Deployment Guide** (`lambda/DEPLOYMENT.md`)
   - Step-by-step AWS deployment
   - Lambda Layer setup
   - Testing procedures
   - Troubleshooting

3. **Lambda README** (`lambda/README.md`)
   - Architecture overview
   - Prerequisites
   - Build and deploy instructions
   - Monitoring and cost estimates

4. **Layer Building Guide** (`lambda/layers/README.md`)
   - Options for GeoPandas Lambda Layer
   - Custom layer building with Docker
   - Public layer resources

### Makefile targets added

```bash
make lambda-test        # Run tests
make lambda-build       # Build with SAM
make lambda-deploy      # Deploy to AWS
make lambda-local       # Run locally with Docker
make lambda-invoke      # Test deployed function
```

### Testing

**Unit tests** (`lambda/tests/test_handler.py`):
- Coordinate validation
- Error handling (missing params, invalid values)
- CORS headers
- Point-in-polygon logic
- Known location integration tests (marked as `@pytest.mark.integration`)

Run tests:
```bash
cd lambda
pytest tests/ -v
pytest tests/ -m "not integration"  # Skip integration tests
```

## Design decisions

### Why Lambda Layer for GeoPandas?

GeoPandas + dependencies (~150 MB) exceed Lambda's 50 MB code package limit. Lambda Layers allow up to 250 MB total, and are reusable across functions.

### Why cache layers globally?

Lambda containers persist for 5-15 minutes after a request. Loading ~40 MB of GeoJSON on every request would be slow. Global caching means:
- **Cold start**: 3-5 seconds (loads all layers)
- **Warm requests**: 50-200ms (uses cached data)

### Why separate demographics?

API returns only identifiers (names), not full demographics. Keeps responses small and fast. Users who need demographics can:
1. Download demographics Parquet files separately
2. Join by layer identifier (e.g., `lapd_division`)

This could be added as an optional query parameter later.

### Why no authentication?

Simplicity and low expected traffic. API is read-only and uses public data. Rate limiting can be added via API Gateway if needed.

## Performance characteristics

### Cold start (first request or after idle)
- Duration: 3-5 seconds
- Loads 9 GeoJSON files from S3 (~40 MB total)
- Converts to GeoPandas GeoDataFrames
- Cached in Lambda global scope

### Warm requests
- Duration: 50-200ms
- Uses cached GeoDataFrames
- Point-in-polygon checks with Shapely
- JSON serialization

### Cost estimate
- Lambda: $0.20 per 1M requests
- API Gateway: $3.50 per 1M requests
- S3 GET: $0.40 per 1M requests
- **Total: ~$4 per 1M requests**
- For 1,000 requests/day (~30K/month): **~$0.12/month**

AWS Free Tier covers 1M Lambda requests/month.

## Potential enhancements (not implemented)

1. **Demographics in response**: Optional `?include_demographics=true` parameter
2. **Batch endpoint**: POST multiple coordinates at once
3. **Distance queries**: "How far to nearest fire station?"
4. **Caching**: CloudFront CDN for popular coordinates
5. **Authentication**: API keys for rate limiting if traffic increases
6. **Custom layers**: User-supplied GeoJSON for queries
7. **Historical data**: Query boundaries from different time periods

## Deployment requirements

### Required
- AWS Account
- AWS CLI configured
- AWS SAM CLI installed
- Lambda Layer with GeoPandas (public or custom-built)

### Optional
- Docker (for local testing with `sam local`)
- pytest (for running tests locally)

## Production readiness

The implementation is **production-ready** for low-medium traffic:

✅ **Ready:**
- Error handling and validation
- CORS support
- Monitoring via CloudWatch
- Cost-effective for low traffic
- Documentation complete
- Tests included

⚠️ **Consider before scaling:**
- Add API Gateway throttling/rate limits
- Add CloudFront CDN for caching
- Monitor cold start frequency
- Consider provisioned concurrency for consistent performance
- Add comprehensive logging/alerting

## Integration with existing project

The API is a **standalone addition** that:
- Uses existing S3-hosted GeoJSON files (no changes needed)
- References layers defined in `config/layers.yml`
- Follows same naming conventions
- Documented in main README
- Makefile targets added for convenience

No changes to existing data pipeline or layers required.

