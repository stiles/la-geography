#!/bin/bash
set -e

# Build MINIMAL Lambda Layer (Shapely only, no GeoPandas)
# Handler will use shapely + requests + json (all simple deps)

echo "🏗️  Building Minimal Lambda Layer for Python 3.11..."
echo ""
echo "Note: Shapely only (no GeoPandas) - handler uses pure Python + Shapely"
echo ""

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Clean up previous builds
echo "🧹 Cleaning up previous builds..."
rm -rf build/
rm -f shapely-layer.zip

# Create build directory
mkdir -p build/python

echo ""
echo "📦 Building layer in Docker (Lambda Python 3.11 environment)..."
echo "   This should take ~1 minute..."
echo ""

# Build in Docker
docker run --rm \
  --entrypoint /bin/bash \
  -v "$(pwd)/build:/build" \
  -w /build \
  public.ecr.aws/lambda/python:3.11 \
  -c "
    echo '📥 Installing Python packages (binary wheels only)...'
    pip install -t /build/python \
      shapely==2.0.2 \
      --only-binary=:all: \
      --platform manylinux2014_x86_64 \
      --python-version 311 \
      --implementation cp \
      --no-deps
    
    # Then install numpy separately with binary wheel
    pip install -t /build/python \
      'numpy<2' \
      --only-binary=:all: \
      --platform manylinux2014_x86_64 \
      --python-version 311 \
      --implementation cp \
      --no-deps \
      --no-cache-dir
    
    echo '🧹 Cleaning up...'
    cd /build/python
    find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name '*.pyc' -delete
    find . -type f -name '*.so' -exec strip {} + 2>/dev/null || true
    
    echo '✅ Build complete'
    du -sh . | awk '{print \"   Layer size: \" \$1}'
  "

echo ""
echo "📦 Creating ZIP file..."
cd build
zip -r ../shapely-layer.zip python/ -q

cd ..
LAYER_SIZE=$(du -h shapely-layer.zip | awk '{print $1}')
echo "✅ Layer created: shapely-layer.zip (${LAYER_SIZE})"

echo ""
echo "🚀 Ready to upload to AWS Lambda!"
echo ""
echo "  aws lambda publish-layer-version \\"
echo "    --layer-name shapely-python311 \\"
echo "    --description 'Shapely 2.0 for Python 3.11' \\"
echo "    --zip-file fileb://shapely-layer.zip \\"
echo "    --compatible-runtimes python3.11 \\"
echo "    --region us-west-2 \\"
echo "    --profile haekeo"

