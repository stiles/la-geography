# Using a Public GeoPandas/GDAL Layer

Building a GeoPandas layer from scratch is complex due to GDAL dependencies. **The easiest approach is to use a public pre-built layer.**

## Recommended: Use Development Seed's GDAL Layer

Development Seed maintains high-quality public GDAL layers for AWS Lambda:

### For us-west-2 (Oregon)

Try these public layers (check which ones exist):

```bash
export AWS_PROFILE=personal

# Search for public layers in your region
aws lambda list-public-layers --region us-west-2 \
  --compatible-runtime python3.11 \
  --query 'Layers[?contains(LayerName, `gdal`) || contains(LayerName, `geo`)]'
```

### Known Public Layers

Check these community-maintained options:

1. **lambgeo layers** (formerly developmentseed):
   - Check: https://github.com/lambgeo/docker-lambda
   - May have public ARNs in documentation

2. **AWS Public Layer Registry**:
   ```bash
   # List all available public layers
   aws lambda list-public-layers --region us-west-2 --compatible-runtime python3.11
   ```

3. **Serverless Application Repository (SAR)**:
   - Search for "gdal" or "geopandas" in AWS Console → Lambda → Layers → SAR

## Alternative: Simplified Build (Without Fiona)

If you can't find a public layer, you can build a simplified version without Fiona (reduces functionality but works):

```bash
# Edit build_layer.sh to use binary wheels only
pip install -t /build/python \
  geopandas==0.14.0 \
  shapely==2.0.2 \
  pyproj==3.6.1 \
  --only-binary=:all: \
  --no-cache-dir
```

This skips Fiona (file I/O library) but GeoPandas can still read from URLs.

## What to Do Now

### Option 1: Find a public layer (recommended)

Run this to search:
```bash
export AWS_PROFILE=personal

# Simple search
aws lambda list-layers --region us-west-2 | grep -i "geo\|gdal\|pandas"

# Or more targeted
aws lambda list-public-layers --region us-west-2 --compatible-runtime python3.11 \
  --output table
```

If you find a layer ARN like:
```
arn:aws:lambda:us-west-2:123456789:layer:gdal-python311:1
```

Add it to `lambda/template.yaml`:
```yaml
Layers:
  - arn:aws:lambda:us-west-2:123456789:layer:gdal-python311:1
```

### Option 2: Deploy without layer, add later

You can deploy the API infrastructure now and add the layer later:

```bash
cd ../
sam build
sam deploy --guided
```

The function will fail on invoke (import error) but you can update it once you have a layer.

### Option 3: Use a third-party deployment

Some services provide ready-made geospatial Lambda deployments:
- Check AWS Marketplace for "geospatial Lambda"
- Look for "GDAL Lambda layer" repos on GitHub with pre-built layers

## Sorry for the complexity!

Building GeoPandas/GDAL for Lambda from scratch is notoriously difficult due to:
- Binary dependencies (GDAL, GEOS, PROJ)
- Compilation requirements
- Size constraints (250 MB layer limit)

This is why public pre-built layers are strongly recommended for geospatial work on Lambda.

