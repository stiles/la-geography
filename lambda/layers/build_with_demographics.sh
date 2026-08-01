#!/bin/bash
set -e

# Build Lambda Layer with Shapely + Pandas for demographics support
# Includes: shapely (for geometries), pandas + pyarrow (for Parquet demographics)

echo "🏗️  Building Lambda Layer with Demographics Support (Python 3.11)..."
echo ""
echo "Includes: shapely, pandas, pyarrow (for Parquet reading)"
echo ""

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Clean up previous builds
echo "🧹 Cleaning up previous builds..."
rm -rf build/
rm -f shapely-pandas-layer.zip

# Create build directory
mkdir -p build/python

echo ""
echo "📦 Building layer in Docker (Lambda Python 3.11 environment)..."
echo "   This should take ~2-3 minutes..."
echo ""

# Build in Docker
docker run --rm \
  --entrypoint /bin/bash \
  -v "$(pwd)/build:/build" \
  -w /build \
  public.ecr.aws/lambda/python:3.11 \
  -c "
    echo '📥 Installing Python packages...'
    pip install -t /build/python \
      shapely==2.0.2 \
      pandas==2.1.4 \
      pyarrow==14.0.1 \
      numpy==1.26.4 \
      --only-binary=:all: \
      --platform manylinux2014_x86_64 \
      --python-version 311 \
      --implementation cp
    
    echo '🧹 Cleaning up unnecessary files...'
    cd /build/python
    
    # Remove test files
    find . -type d -name 'tests' -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name '*.pyc' -delete
    find . -type f -name '*.pyo' -delete
    
    # Remove pandas extras we don't need
    rm -rf pandas/tests 2>/dev/null || true
    rm -rf pandas/io/clipboard 2>/dev/null || true
    
    # Remove pyarrow extras
    rm -rf pyarrow/tests 2>/dev/null || true
    
    # Strip binaries
    find . -type f -name '*.so' -exec strip {} + 2>/dev/null || true
    
    echo '✅ Build complete'
    du -sh . | awk '{print \"   Layer size: \" \$1}'
  "

echo ""
echo "📦 Creating ZIP file..."
cd build
zip -r ../shapely-pandas-layer.zip python/ -q

cd ..
LAYER_SIZE=$(du -h shapely-pandas-layer.zip | awk '{print $1}')
echo "✅ Layer created: shapely-pandas-layer.zip (${LAYER_SIZE})"

# Check size warning
SIZE_MB=$(du -m shapely-pandas-layer.zip | awk '{print $1}')
if [ "$SIZE_MB" -gt 200 ]; then
    echo ""
    echo "⚠️  Warning: Layer is ${SIZE_MB}MB. Lambda layers are limited to 250MB unzipped."
fi

echo ""
echo "📊 Layer contents:"
unzip -l shapely-pandas-layer.zip | grep -E 'shapely|pandas|pyarrow|numpy' | head -20
echo "   ..."

echo ""
echo "🚀 Ready to upload to AWS Lambda!"
echo ""
echo "Upload command:"
echo "  aws lambda publish-layer-version \\"
echo "    --layer-name shapely-pandas-python311 \\"
echo "    --description 'Shapely + Pandas + PyArrow for Python 3.11' \\"
echo "    --zip-file fileb://shapely-pandas-layer.zip \\"
echo "    --compatible-runtimes python3.11 \\"
echo "    --region us-west-2"
echo ""
echo "Then update your SAM template to use the new layer ARN."

