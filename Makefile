# Makefile for la-geo pipeline
# Usage: make [target]

.PHONY: help fetch standardize validate export quicklook s3-upload s3-download s3-list fetch-census apportion-census apportion-census-test validate-census lambda-layer lambda-test lambda-build lambda-deploy lambda-local lambda-invoke clean all

# Default target
help:
	@echo "LA Geography Pipeline"
	@echo ""
	@echo "Available targets:"
	@echo "  fetch        - Fetch raw layers from configured sources"
	@echo "  standardize  - Clean and normalize raw data (process_raw.py)"
	@echo "  s3-upload    - Upload processed layers to S3"
	@echo "  s3-download  - Download layers from S3"
	@echo "  s3-list      - List available layers in S3"
	@echo ""
	@echo "Census demographics:"
	@echo "  fetch-census        - Fetch 2020 Census blocks and demographics"
	@echo "  apportion-census    - Apportion demographics to all polygon layers"
	@echo "  apportion-census-test - Apportion to LAPD bureaus (test)"
	@echo "  validate-census     - Validate apportionment results"
	@echo ""
	@echo "Point-lookup API (Lambda):"
	@echo "  lambda-layer        - Build GeoPandas Lambda Layer (requires Docker)"
	@echo "  lambda-test         - Run Lambda function unit tests"
	@echo "  lambda-build        - Build Lambda deployment package with SAM"
	@echo "  lambda-deploy       - Deploy Lambda function to AWS"
	@echo "  lambda-domain       - Setup custom domain (api.stilesdata.com)"
	@echo "  lambda-local        - Run Lambda API locally (requires Docker)"
	@echo "  lambda-invoke       - Test deployed Lambda with sample request"
	@echo ""
	@echo "  all          - Run full pipeline (fetch -> standardize)"
	@echo "  clean        - Remove generated files"
	@echo ""
	@echo "Example: make fetch standardize apportion-census"

# Fetch raw layers
fetch:
	@echo "Fetching boundary layers..."
	python scripts/fetch_boundaries.py --out data/raw/
	@echo "✓ Fetch complete"

# Standardize (clean + normalize)
standardize:
	@echo "Standardizing layers..."
	python scripts/process_raw.py --input data/raw/ --output data/standard/
	@echo "✓ Standardization complete"

# Validate geometry and counts
# Note: validate.py not yet implemented - using basic validation from fetch
validate:
	@echo "Note: validate.py not yet implemented"
	@echo "Layers are validated during fetch (see fetch_boundaries.py)"
	@echo "For census validation, use: make validate-census"

# Export to multiple formats
# Note: export.py not yet implemented (layers already exported to data/standard/)
# export:
# 	@echo "Exporting layers..."
# 	python scripts/export.py --input data/standard/
# 	@echo "✓ Export complete"

# Generate quicklook previews
# Note: quicklook.py not yet implemented
# quicklook:
# 	@echo "Generating quicklooks..."
# 	python scripts/quicklook.py --input data/standard/ --output data/docs/
# 	@echo "✓ Quicklooks generated"

# S3 operations
s3-upload:
	@echo "Uploading layers to S3..."
	python scripts/s3_sync.py upload
	@echo "✓ Upload complete"

s3-download:
	@echo "Downloading layers from S3..."
	python scripts/s3_sync.py download
	@echo "✓ Download complete"

s3-list:
	@echo "Listing S3 layers..."
	python scripts/s3_sync.py list

# Census demographics targets
fetch-census:
	@echo "Fetching 2020 Census blocks and demographics..."
	python scripts/fetch_census.py
	@echo "✓ Census fetch complete"

apportion-census:
	@echo "Apportioning Census data to all polygon layers..."
	python scripts/apportion_census.py --all
	@echo "✓ Census apportionment complete"

apportion-census-test:
	@echo "Apportioning Census data to LAPD bureaus (test)..."
	python scripts/apportion_census.py --layer lapd_bureaus
	@echo "✓ Test apportionment complete"

validate-census:
	@echo "Validating Census apportionment results..."
	python scripts/validate_apportionment.py --all
	@echo "✓ Census validation complete"

# Run full pipeline
all: fetch standardize
	@echo "✓ Full pipeline complete"

# Lambda function targets
lambda-layer:
	@echo "Building GeoPandas Lambda Layer..."
	cd lambda/layers && ./build_layer.sh
	@echo ""
	@echo "✓ Layer built successfully!"
	@echo ""
	@echo "To upload to AWS, run:"
	@echo "  cd lambda/layers"
	@echo "  aws lambda publish-layer-version \\"
	@echo "    --layer-name geopandas-python311 \\"
	@echo "    --description 'GeoPandas for Python 3.11' \\"
	@echo "    --zip-file fileb://geopandas-layer.zip \\"
	@echo "    --compatible-runtimes python3.11 \\"
	@echo "    --region us-west-2 \\"
	@echo "    --profile personal"

lambda-test:
	@echo "Running Lambda function tests..."
	cd lambda && pytest tests/ -v
	@echo "✓ Tests complete"

lambda-build:
	@echo "Building Lambda function with SAM..."
	cd lambda && sam build
	@echo "✓ Build complete"

lambda-deploy:
	@echo "Deploying Lambda function to AWS..."
	cd lambda && sam deploy
	@echo "✓ Deploy complete"

lambda-domain:
	@echo "Setting up custom domain for API..."
	cd lambda && ./setup_custom_domain.sh
	@echo "✓ Custom domain setup complete"

lambda-local:
	@echo "Starting Lambda API locally (requires Docker)..."
	@echo "API will be available at http://127.0.0.1:3000/lookup"
	@echo "Test with: curl 'http://127.0.0.1:3000/lookup?lat=34.0522&lon=-118.2437'"
	@echo ""
	cd lambda && sam local start-api

lambda-invoke:
	@echo "Testing deployed Lambda function..."
	@echo "Querying Downtown LA (34.0522, -118.2437)..."
	aws lambda invoke \
		--function-name $$(aws cloudformation describe-stacks \
			--stack-name la-geography-lookup-api \
			--query 'Stacks[0].Outputs[?OutputKey==`FunctionName`].OutputValue' \
			--output text) \
		--payload '{"queryStringParameters": {"lat": "34.0522", "lon": "-118.2437"}}' \
		--cli-binary-format raw-in-base64-out \
		/dev/stdout | jq .
	@echo ""
	@echo "✓ Test complete"

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	rm -rf data/standard/*
	rm -rf data/docs/*
	rm -rf lambda/.aws-sam/
	@echo "✓ Clean complete"

