# Quick start: Deploy the point-lookup API

**5 minute guide** to get your API running on AWS.

## Prerequisites

✅ AWS Account  
✅ AWS CLI configured (`aws configure`)  
✅ [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) installed

```bash
# Install SAM CLI
brew install aws-sam-cli  # macOS
# or: pip install aws-sam-cli
```

## Step 1: Choose a GeoPandas Lambda Layer

Edit `template.yaml` and uncomment a layer option:

**Option A - Public layer** (recommended):
```yaml
Layers:
  - arn:aws:lambda:us-west-2:524387336408:layer:gdal38-py311:1
```

**Option B - Build your own**:
```bash
cd layers && ./build_layer.sh
# Follow prompts to upload, then add ARN to template.yaml
```

See [layers/README.md](layers/README.md) for details.

## Step 2: Build & Deploy

```bash
cd lambda/

# Build
sam build

# Deploy (first time - guided)
sam deploy --guided
```

**Prompts** (use defaults):
- Stack name: `la-geography-lookup-api` ✓
- Region: `us-west-2` ✓
- Confirm changes: `Y` ✓
- Allow IAM role creation: `Y` ✓
- Save config: `Y` ✓

**Wait 2-3 minutes** for CloudFormation to create resources.

## Step 3: Get Your API URL

After deployment:
```
Outputs
-----------------------------------------------------------------------
Key                 ApiEndpoint
Value               https://abc123xyz.execute-api.us-west-2.amazonaws.com/prod/lookup
-----------------------------------------------------------------------
```

**Save this URL!** This is your API endpoint.

## Step 4: Test It

```bash
# Replace with your actual API URL
API_URL="https://YOUR-API-ID.execute-api.us-west-2.amazonaws.com/prod/lookup"

# Test Downtown LA
curl "${API_URL}?lat=34.0522&lon=-118.2437"
```

**Expected response:**
```json
{
  "status": "success",
  "query": {"lat": 34.0522, "lon": -118.2437},
  "results": {
    "neighborhood": "Downtown",
    "city": "Los Angeles",
    "lapd_division": "Central",
    ...
  }
}
```

## Step 5: Update Documentation

Update `docs/API.md` with your actual API URL:

```markdown
**Endpoint**: `https://YOUR-API-ID.execute-api.us-west-2.amazonaws.com/prod/lookup`
```

---

## Done! 🎉

Your API is live and ready to use.

### Next Steps

- **Test more locations**: `python examples/test_api.py <your-api-url>`
- **Monitor**: `sam logs -n LookupFunction --tail`
- **Update code**: `sam build && sam deploy`
- **Delete**: `sam delete` (removes everything)

### Cost

~$0.30/month for 1,000 requests/day (well within AWS Free Tier)

### Need Help?

- [Full Deployment Guide](DEPLOYMENT.md)
- [API Documentation](../docs/API.md)
- [Layer Setup Guide](layers/README.md)
- [Implementation Notes](../IMPLEMENTATION_NOTES.md)

