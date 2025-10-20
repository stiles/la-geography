# Makefile for la-geo pipeline
# Usage: make [target]

.PHONY: help fetch standardize validate export quicklook s3-upload s3-download s3-list clean all

# Default target
help:
	@echo "LA Geography Pipeline"
	@echo ""
	@echo "Available targets:"
	@echo "  fetch        - Fetch raw layers from configured sources"
	@echo "  standardize  - Clean and normalize raw data"
	@echo "  validate     - Run geometry and count checks"
	@echo "  export       - Export to GeoJSON + Parquet in data/standard"
	@echo "  quicklook    - Generate preview images"
	@echo "  s3-upload    - Upload processed layers to S3"
	@echo "  s3-download  - Download layers from S3"
	@echo "  s3-list      - List available layers in S3"
	@echo "  all          - Run full pipeline (fetch -> export)"
	@echo "  clean        - Remove generated files"
	@echo ""
	@echo "Example: make fetch standardize validate export s3-upload"

# Fetch raw layers
fetch:
	@echo "Fetching boundary layers..."
	python scripts/fetch_boundaries.py --out data/raw/
	@echo "✓ Fetch complete"

# Standardize (clean + normalize)
standardize:
	@echo "Standardizing layers..."
	python scripts/standardize.py --input data/raw/ --output data/standard/
	@echo "✓ Standardization complete"

# Validate geometry and counts
validate:
	@echo "Validating layers..."
	python scripts/validate.py --input data/standard/
	@echo "✓ Validation complete"

# Export to multiple formats
export:
	@echo "Exporting layers..."
	python scripts/export.py --input data/standard/
	@echo "✓ Export complete"

# Generate quicklook previews
quicklook:
	@echo "Generating quicklooks..."
	python scripts/quicklook.py --input data/standard/ --output data/docs/
	@echo "✓ Quicklooks generated"

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

# Run full pipeline
all: fetch standardize validate export
	@echo "✓ Full pipeline complete"

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	rm -rf data/standard/*
	rm -rf data/docs/*
	@echo "✓ Clean complete"

