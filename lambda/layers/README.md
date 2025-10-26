# Building a GeoPandas Lambda Layer

GeoPandas and its dependencies (GDAL, GEOS, Fiona, pyproj) are too large for a standard Lambda deployment package. You need to create a Lambda Layer with these libraries.

## Option 1: Use a pre-built layer (recommended)

Several community-maintained layers are available:

### lambgeo/lambda-gdal

The [lambgeo](https://github.com/lambgeo) organization maintains well-tested GDAL layers for AWS Lambda:

**Public ARNs** (check for latest versions):
```
# us-west-2 (Oregon)
arn:aws:lambda:us-west-2:524387336408:layer:gdal38-py311:1

# us-east-1 (N. Virginia)
arn:aws:lambda:us-east-1:524387336408:layer:gdal38-py311:1
```

**To use**: Add to your `template.yaml`:
```yaml
Layers:
  - arn:aws:lambda:us-west-2:524387336408:layer:gdal38-py311:1
```

### Check AWS Serverless Application Repository

Search for "geopandas" or "gdal" layers:
- AWS Console → Lambda → Layers → Add layer → AWS Layers or Serverless Application Repository
- Look for Python 3.11 compatible layers
- Check layer size (should be ~40-50 MB for GeoPandas)

## Option 2: Build your own layer

If you need a custom configuration or can't find a compatible pre-built layer:

### Prerequisites

- Docker (for building in Lambda-compatible environment)
- AWS CLI configured

### Steps

#### 1. Create build script

Create `lambda/layers/build_layer.sh`:

```bash
#!/bin/bash
set -e

# Build GeoPandas layer for AWS Lambda (Python 3.11)

echo "Building GeoPandas Lambda Layer..."

# Create build directory
mkdir -p build/python

# Build in Docker (matches Lambda environment)
docker run --rm \
  -v $(pwd)/build:/build \
  -w /build \
  public.ecr.aws/lambda/python:3.11 \
  bash -c "
    pip install -t /build/python \
      geopandas==0.14.0 \
      shapely==2.0.2 \
      pyproj==3.6.1 \
      fiona==1.9.5 \
      --no-cache-dir
    
    # Clean up to reduce size
    cd /build/python
    find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name '*.pyc' -delete
    find . -type f -name '*.so' -exec strip {} + 2>/dev/null || true
    
    du -sh .
  "

echo "Creating layer ZIP..."
cd build
zip -r ../geopandas-layer.zip python/ -q

echo "Done! Layer size:"
du -h ../geopandas-layer.zip

echo ""
echo "Upload to AWS Lambda:"
echo "aws lambda publish-layer-version \\"
echo "  --layer-name geopandas-python311 \\"
echo "  --description 'GeoPandas and dependencies for Python 3.11' \\"
echo "  --zip-file fileb://geopandas-layer.zip \\"
echo "  --compatible-runtimes python3.11"
```

Make it executable:
```bash
chmod +x lambda/layers/build_layer.sh
```

#### 2. Build the layer

```bash
cd lambda/layers
./build_layer.sh
```

This creates `geopandas-layer.zip` (~40-50 MB).

#### 3. Upload to AWS Lambda

```bash
aws lambda publish-layer-version \
  --layer-name geopandas-python311 \
  --description "GeoPandas and dependencies for Python 3.11" \
  --zip-file fileb://geopandas-layer.zip \
  --compatible-runtimes python3.11
```

**Output** includes the Layer ARN:
```
{
    "LayerArn": "arn:aws:lambda:us-west-2:123456789012:layer:geopandas-python311",
    "LayerVersionArn": "arn:aws:lambda:us-west-2:123456789012:layer:geopandas-python311:1",
    ...
}
```

#### 4. Update template.yaml

Add the layer ARN to your SAM template:
```yaml
Layers:
  - arn:aws:lambda:us-west-2:123456789012:layer:geopandas-python311:1
```

## Option 3: Use AWS Lambda Layers from public repositories

Some organizations publish public Lambda layers:

### Development Seed (developmentseed)

Development Seed maintains geospatial layers:
- GitHub: https://github.com/developmentseed/lambda-gdal
- Check releases for layer ARNs

### Coiled (formerly Pangeo)

Coiled/Pangeo maintains scientific Python layers:
- May include GeoPandas/GDAL packages
- Check their documentation for public ARNs

## Troubleshooting

### "Unable to import module 'handler'"

**Cause**: Layer doesn't include required dependencies or wrong Python version

**Fix**:
1. Verify layer is Python 3.11 compatible
2. Check layer includes: geopandas, shapely, fiona, pyproj, GDAL
3. Test locally with `sam local start-api`

### Layer too large (>250 MB uncompressed)

**Cause**: Layer exceeds Lambda's 250 MB limit

**Fix**:
1. Remove unnecessary files (tests, docs, examples)
2. Strip debug symbols from .so files
3. Use lighter alternatives (e.g., shapely without GDAL)

### Missing native dependencies

**Cause**: GDAL/GEOS native libraries not included

**Fix**:
1. Build in Lambda Docker image (ensures correct binaries)
2. Use pre-built layers from lambgeo or Development Seed

## Verify layer contents

After uploading, verify the layer works:

```bash
# Download and inspect
aws lambda get-layer-version \
  --layer-name geopandas-python311 \
  --version-number 1 \
  --query 'Content.Location' \
  --output text | xargs curl -o layer.zip

unzip -l layer.zip | grep geopandas
```

Test locally:
```bash
cd lambda
sam local start-api
curl "http://127.0.0.1:3000/lookup?lat=34.0522&lon=-118.2437"
```

## Cost

Lambda Layers are free (no additional charge beyond Lambda execution).

Storage:
- Layer storage: $0.03/GB-month
- 50 MB layer ≈ $0.0015/month

## References

- [AWS Lambda Layers](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
- [lambgeo/lambda-gdal](https://github.com/lambgeo/docker-lambda)
- [Development Seed Lambda GDAL](https://github.com/developmentseed/lambda-gdal)
- [Building Lambda Layers](https://aws.amazon.com/blogs/compute/working-with-lambda-layers-and-extensions-in-container-images/)

