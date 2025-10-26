#!/bin/bash
set -e

# Build GeoPandas Lambda Layer for Python 3.11
# Uses Docker to create Lambda-compatible binaries

echo "🏗️  Building GeoPandas Lambda Layer for Python 3.11..."
echo ""

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Clean up previous builds
echo "🧹 Cleaning up previous builds..."
rm -rf build/
rm -f geopandas-layer.zip

# Create build directory
mkdir -p build/python

echo ""
echo "📦 Building layer in Docker (Lambda Python 3.11 environment)..."
echo "   This may take 3-5 minutes..."
echo ""

# Build in Docker (matches Lambda environment exactly)
docker run --rm \
  --entrypoint /bin/bash \
  -v "$(pwd)/build:/build" \
  -w /build \
  public.ecr.aws/lambda/python:3.11 \
  -c "
    echo '📦 Installing system dependencies (GDAL)...'
    yum install -y gdal-devel gcc-c++ &>/dev/null || echo 'System packages install failed'
    
    echo '📥 Installing Python packages...'
    pip install -t /build/python \
      geopandas==0.14.0 \
      shapely==2.0.2 \
      pyproj==3.6.1 \
      fiona==1.9.5 \
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
zip -r ../geopandas-layer.zip python/ -q

cd ..
LAYER_SIZE=$(du -h geopandas-layer.zip | awk '{print $1}')
echo "✅ Layer created: geopandas-layer.zip (${LAYER_SIZE})"

echo ""
echo "🚀 Ready to upload to AWS Lambda!"
echo ""
echo "To upload, run:"
echo ""
echo "  aws lambda publish-layer-version \\"
echo "    --layer-name geopandas-python311 \\"
echo "    --description 'GeoPandas and dependencies for Python 3.11' \\"
echo "    --zip-file fileb://geopandas-layer.zip \\"
echo "    --compatible-runtimes python3.11 \\"
echo "    --region us-west-2 \\"
echo "    --profile personal"
echo ""
echo "After uploading, copy the LayerVersionArn from the output"
echo "and add it to lambda/template.yaml"

