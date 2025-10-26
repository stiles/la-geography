# LA Geography Point-Lookup API - Lambda Deployment

AWS Lambda function that performs point-in-polygon queries to determine which geographic features (neighborhood, city, police division, fire station, etc.) contain a given lat/lon coordinate.

## Architecture

- **Lambda Function**: Python 3.11 with GeoPandas for spatial queries
- **API Gateway**: Public HTTPS endpoint
- **Data Source**: GeoJSON files loaded from S3 (stilesdata.com/la-geography)
- **Caching**: Layers cached in Lambda global scope across warm invocations

## Prerequisites

1. **AWS Account** with permissions for Lambda, API Gateway, CloudFormation/SAM
2. **AWS CLI** configured with credentials
3. **AWS SAM CLI** installed (for deployment)
   ```bash
   # Install SAM CLI
   brew install aws-sam-cli  # macOS
   # or pip install aws-sam-cli
   ```
4. **Docker** (for building Lambda layer with GeoPandas)

## Lambda Layer for GeoPandas

GeoPandas and its dependencies (GDAL, GEOS, Fiona, etc.) are too large (~150 MB) for a standard Lambda deployment package (50 MB limit). You need to provide these via a Lambda Layer.

### Option 1: Use a pre-built layer (easiest)

Search AWS Serverless Application Repository for "geopandas" or "gdal" layers:

```bash
# Search for available layers
sam deploy --guided --template layers.yaml
```

Some community layers:
- [lambgeo/lambda-gdal](https://github.com/lambgeo/docker-lambda) - Well-maintained GDAL layers
- AWS Public Layers (check SAR for Python 3.11 compatible versions)

Update `template.yaml` with the layer ARN:
```yaml
Layers:
  - arn:aws:lambda:us-west-2:123456789012:layer:geopandas-python311:1
```

### Option 2: Build your own layer

See `layers/README.md` for instructions on building a custom GeoPandas layer using Docker.

## Deployment

### Step 1: Build the function

```bash
cd lambda/
sam build
```

This packages the Lambda function code and resolves dependencies.

### Step 2: Deploy

First deployment (creates resources):
```bash
sam deploy --guided
```

Follow the prompts:
- Stack name: `la-geography-lookup-api`
- Region: `us-west-2` (or your preferred region)
- Confirm changes before deploy: `Y`
- Allow SAM CLI IAM role creation: `Y`
- Save arguments to config file: `Y`

Subsequent deployments (uses saved config):
```bash
sam deploy
```

### Step 3: Get the API endpoint

After deployment, SAM outputs the API Gateway URL:
```
Outputs
-----------------------------------------------------------------------
Key: ApiEndpoint
Value: https://abc123xyz.execute-api.us-west-2.amazonaws.com/prod/lookup
```

## Testing

### Test with curl

```bash
# Downtown LA
curl "https://YOUR-API-ID.execute-api.us-west-2.amazonaws.com/prod/lookup?lat=34.0522&lon=-118.2437"

# Venice Beach
curl "https://YOUR-API-ID.execute-api.us-west-2.amazonaws.com/prod/lookup?lat=33.9850&lon=-118.4695"

# Pasadena
curl "https://YOUR-API-ID.execute-api.us-west-2.amazonaws.com/prod/lookup?lat=34.1478&lon=-118.1445"
```

### Test with Python

```python
import requests

endpoint = "https://YOUR-API-ID.execute-api.us-west-2.amazonaws.com/prod/lookup"
response = requests.get(endpoint, params={"lat": 34.0522, "lon": -118.2437})
print(response.json())
```

### Local testing

Test the Lambda function locally using SAM:

```bash
# Start local API
sam local start-api

# In another terminal, test the endpoint
curl "http://127.0.0.1:3000/lookup?lat=34.0522&lon=-118.2437"
```

**Note**: Local testing requires Docker and may have long cold starts (3-5 seconds) while loading GeoJSON data.

## Monitoring

### CloudWatch Logs

View function logs:
```bash
sam logs -n LookupFunction --stack-name la-geography-lookup-api --tail
```

### Metrics

Monitor in AWS Console:
- Lambda > Functions > la-geography-lookup-api-LookupFunction
- Key metrics: Invocations, Duration, Errors, Throttles

## Cost Estimate

For low-medium traffic (1,000 requests/day):

- **Lambda**: ~$0.20/month
  - 30K requests/month
  - 512 MB memory, ~500ms average duration (warm)
  - Cold starts: ~3-5 seconds (first request or after idle)
  
- **API Gateway**: ~$0.10/month
  - 30K requests/month
  
- **Data Transfer**: Negligible (small JSON responses)

**Total**: ~$0.30/month (well within AWS Free Tier)

Free tier includes:
- Lambda: 1M requests/month + 400K GB-seconds compute
- API Gateway: 1M requests/month (first 12 months)

## Performance

- **Cold start**: 3-5 seconds (loading ~40 MB GeoJSON from S3)
- **Warm requests**: 50-200ms (depends on point location and layer complexity)
- **Caching**: Layers cached in global scope, reused across invocations
- **Lambda lifecycle**: Warm for 5-15 minutes after last request

### Optimization tips

If cold starts become an issue:
1. **Provisioned concurrency** - Keep Lambda warm (costs more)
2. **CloudWatch Events** - Ping function every 5 minutes to keep warm
3. **Smaller data formats** - Pre-process to GeoParquet or spatial index
4. **CloudFront caching** - Cache responses for popular coordinates

## Updating the Function

After making code changes:

```bash
cd lambda/
sam build
sam deploy
```

To update layer configuration:
1. Edit `template.yaml` (add/change layer ARN)
2. Run `sam deploy`

## Cleanup

To delete all resources:

```bash
sam delete --stack-name la-geography-lookup-api
```

This removes:
- Lambda function
- API Gateway
- CloudFormation stack
- IAM roles

## Troubleshooting

### "Unable to import module 'handler'"

GeoPandas layer is missing or incompatible. Check:
1. Layer ARN is correct in `template.yaml`
2. Layer is compatible with Python 3.11
3. Layer includes: geopandas, shapely, fiona, pyproj, GDAL

### "Execution time exceeded timeout"

Cold start is taking too long. Options:
1. Increase timeout in `template.yaml` (currently 30s)
2. Increase memory (more CPU allocated)
3. Optimize data loading (use smaller formats)

### "403 Forbidden" on S3 requests

Lambda needs permission to read from S3. The function loads public URLs, so no special permissions needed. Check that S3 URLs are publicly accessible.

## See Also

- [API Documentation](../docs/API.md) - Public API reference
- [Layer Building Guide](layers/README.md) - Build custom GeoPandas layer
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)

