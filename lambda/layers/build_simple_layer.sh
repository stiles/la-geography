#!/bin/bash
set -e

# Build SIMPLIFIED GeoPandas Lambda Layer (no GDAL/Fiona)
# This version works for reading GeoJSON from HTTPS URLs
# (which is all we need for this project)

echo "🏗️  Building Simplified GeoPandas Lambda Layer for Python 3.11..."
echo ""
echo "Note: This version skips Fiona/GDAL (not needed for reading from HTTPS)"
echo ""

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Clean up previous builds
echo "🧹 Cleaning up previous builds..."
rm -rf build/
rm -f geopandas-layer-simple.zip

# Create build directory
mkdir -p build/python

echo ""
echo "📦 Building layer in Docker (Lambda Python 3.11 environment)..."
echo "   This should take 1-2 minutes..."
echo ""

# Build in Docker (matches Lambda environment exactly)
docker run --rm \
  --entrypoint /bin/bash \
  -v "$(pwd)/build:/build" \
  -w /build \
  public.ecr.aws/lambda/python:3.11 \
  -c "
    echo '📥 Installing Python packages (binary wheels only)...'
    pip install -t /build/python \
      geopandas==0.14.0 \
      shapely==2.0.2 \
      pyproj==3.6.1 \
      --only-binary=:all: \
      --no-cache-dir
    
    echo '🧹 Cleaning up unnecessary files...'
    cd /build/python
    
    # Remove __pycache__ and .pyc files
    find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name '*.pyc' -delete
    
    # Remove tests and docs
    find . -type d -name 'tests' -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name 'docs' -exec rm -rf {} + 2>/dev/null || true
    
    # Strip binaries to reduce size
    find . -type f -name '*.so' -exec strip {} + 2>/dev/null || true
    
    echo '✅ Build complete'
    du -sh . | awk '{print \"   Layer size: \" \$1}'
  "

echo ""
echo "📦 Creating ZIP file..."
cd build
zip -r ../geopandas-layer-simple.zip python/ -q

cd ..
LAYER_SIZE=$(du -h geopandas-layer-simple.zip | awk '{print $1}')
echo "✅ Layer created: geopandas-layer-simple.zip (${LAYER_SIZE})"

echo ""
echo "🚀 Ready to upload to AWS Lambda!"
echo ""
echo "To upload, run:"
echo ""
echo "  aws lambda publish-layer-version \\"
echo "    --layer-name geopandas-simple-python311 \\"
echo "    --description 'GeoPandas (simplified, no GDAL) for Python 3.11' \\"
echo "    --zip-file fileb://geopandas-layer-simple.zip \\"
echo "    --compatible-runtimes python3.11 \\"
echo "    --region us-west-2 \\"
echo "    --profile haekeo"
echo ""
echo "After uploading, copy the LayerVersionArn from the output"
echo "and add it to lambda/template.yaml"

