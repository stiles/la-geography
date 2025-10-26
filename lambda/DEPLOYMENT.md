# Quick deployment guide

Step-by-step guide to deploy the point-lookup API to AWS Lambda.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
   ```bash
   aws configure
   ```
3. **AWS SAM CLI** installed
   ```bash
   # macOS
   brew install aws-sam-cli
   
   # Or via pip
   pip install aws-sam-cli
   ```
4. **Docker** installed (for building and local testing)

## Step 1: Configure Lambda Layer

The function requires GeoPandas and GDAL, which must be provided via a Lambda Layer.

### Option A: Use a public layer (recommended)

Edit `template.yaml` and uncomment the `Layers` section with a public GeoPandas/GDAL layer ARN:

```yaml
Layers:
  # Option 1: Use lambgeo's public GDAL layer (Python 3.11)
  - arn:aws:lambda:us-west-2:524387336408:layer:gdal38-py311:1
```

**Public layer resources:**
- lambgeo/lambda-gdal: https://github.com/lambgeo/docker-lambda
- Check for latest ARNs and regional availability

### Option B: Build your own layer

If no public layer is available for your region:

```bash
cd layers
./build_layer.sh  # Creates geopandas-layer.zip

# Upload to Lambda
aws lambda publish-layer-version \
  --layer-name geopandas-python311 \
  --description "GeoPandas for Python 3.11" \
  --zip-file fileb://geopandas-layer.zip \
  --compatible-runtimes python3.11

# Note the LayerVersionArn from output and add to template.yaml
```

See `layers/README.md` for detailed instructions.

## Step 2: Build the function

```bash
cd lambda/
sam build
```

This creates a deployment package in `.aws-sam/build/`.

## Step 3: Deploy to AWS

### First deployment (guided)

```bash
sam deploy --guided
```

Answer prompts:
- **Stack Name**: `la-geography-lookup-api` (default)
- **AWS Region**: `us-west-2` (or your preferred region)
- **Confirm changes before deploy**: `Y`
- **Allow SAM CLI IAM role creation**: `Y`
- **Disable rollback**: `N`
- **Save arguments to configuration file**: `Y`
- **SAM configuration file**: `samconfig.toml` (default)
- **SAM configuration environment**: `default` (default)

This creates:
- Lambda function
- API Gateway REST API
- IAM execution role
- CloudFormation stack

### Subsequent deployments

After first deployment, simply run:
```bash
sam deploy
```

## Step 4: Get your API endpoint

After deployment completes, SAM outputs the API URL:

```
CloudFormation outputs from deployed stack
-------------------------------------------------------------------
Outputs
-------------------------------------------------------------------
Key                 ApiEndpoint
Description         API Gateway endpoint URL for point-lookup
Value               https://abc123xyz.execute-api.us-west-2.amazonaws.com/prod/lookup
-------------------------------------------------------------------
```

Save this URL - this is your public API endpoint!

## Step 5: Test the API

### Test with curl

```bash
# Replace with your actual API Gateway URL
API_URL="https://YOUR-API-ID.execute-api.us-west-2.amazonaws.com/prod/lookup"

# Downtown LA
curl "${API_URL}?lat=34.0522&lon=-118.2437"

# Venice Beach
curl "${API_URL}?lat=33.9850&lon=-118.4695"

# Pasadena
curl "${API_URL}?lat=34.1478&lon=-118.1445"
```

### Test with AWS CLI

```bash
make lambda-invoke
```

### Check CloudWatch logs

```bash
sam logs -n LookupFunction --stack-name la-geography-lookup-api --tail
```

## Step 6: Update your documentation

Update `docs/API.md` with your actual API endpoint URL:

```markdown
**Endpoint**: `https://YOUR-API-ID.execute-api.us-west-2.amazonaws.com/prod/lookup`
```

## Monitoring

### CloudWatch Metrics

View metrics in AWS Console:
- Lambda → Functions → la-geography-lookup-api-LookupFunction
- Monitor: Invocations, Duration, Errors, Throttles

### CloudWatch Logs

View logs:
```bash
sam logs -n LookupFunction --stack-name la-geography-lookup-api --tail
```

### Cost monitoring

Monitor costs in AWS Cost Explorer:
- Lambda charges: Invocations + compute time
- API Gateway charges: Requests
- Data transfer: Outbound data

Expected: $0.30-$0.50/month for low traffic (<1000 requests/day)

## Updating the function

After code changes:

```bash
cd lambda/
sam build
sam deploy
```

Changes are deployed with zero downtime (Lambda versioning).

## Troubleshooting

### Cold start timeout

**Symptom**: First request times out or takes >30 seconds

**Solution**: Increase timeout in `template.yaml`:
```yaml
Timeout: 60  # Increase from 30 to 60 seconds
```

Then redeploy:
```bash
sam deploy
```

### "Unable to import module 'handler'"

**Symptom**: Lambda can't import geopandas

**Solution**: 
1. Verify layer ARN in `template.yaml` is correct
2. Check layer is compatible with Python 3.11
3. Ensure layer includes: geopandas, shapely, fiona, pyproj, GDAL

### 403 Forbidden when loading data from S3

**Symptom**: Lambda can't read GeoJSON from S3

**Solution**: 
- Verify S3 URLs are publicly accessible
- Test URLs directly: `curl https://stilesdata.com/la-geography/lapd_bureaus.geojson`

### Memory issues

**Symptom**: Lambda runs out of memory

**Solution**: Increase memory in `template.yaml`:
```yaml
MemorySize: 1024  # Increase from 512 to 1024 MB
```

More memory = more CPU, faster cold starts.

## Cleanup

To delete all resources:

```bash
sam delete --stack-name la-geography-lookup-api
```

This removes:
- Lambda function
- API Gateway
- IAM roles
- CloudFormation stack

## Next steps

1. **Add custom domain** - Use Route53 + API Gateway custom domain
2. **Add CloudFront** - Cache responses for better performance
3. **Add API key** - Implement light rate limiting if needed
4. **Add monitoring alerts** - CloudWatch alarms for errors/throttles

## Resources

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [API Gateway Documentation](https://docs.aws.amazon.com/apigateway/)

