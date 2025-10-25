#!/usr/bin/env python3
"""
S3 Sync for LA Geography Boundaries

Upload/download processed boundary layers and demographics to/from S3 for public distribution.

Usage:
    python scripts/s3_sync.py upload [--layer LAYER_NAME] [--no-demographics]
    python scripts/s3_sync.py download [--layer LAYER_NAME] [--no-demographics]
    python scripts/s3_sync.py list

By default, both boundaries (.geojson) and demographics (.parquet) files are synced.
Use --no-demographics to sync only boundaries.

Environment Variables:
    MY_AWS_ACCESS_KEY_ID     - AWS access key
    MY_AWS_SECRET_ACCESS_KEY - AWS secret key
    MY_PERSONAL_PROFILE      - AWS profile name (for clarity)
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime
import json

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import yaml

# S3 Configuration
S3_BUCKET = "stilesdata.com"
S3_PREFIX = "la-geography"

# Standard layers directory
STANDARD_DIR = Path("data/standard")
CONFIG_FILE = Path("config/layers.yml")


def get_layers_from_config():
    """
    Read layer names from config/layers.yml to ensure we're always in sync.
    Falls back to discovering .geojson files if config is not available.
    """
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            config = yaml.safe_load(f)
            return list(config.keys())
    else:
        # Fallback: discover from filesystem
        return [
            p.stem for p in STANDARD_DIR.glob("*.geojson")
            if p.stem != "metadata"
        ]


def get_s3_client():
    """
    Create S3 client using personal AWS credentials from environment.
    """
    access_key = os.getenv("MY_AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("MY_AWS_SECRET_ACCESS_KEY")
    profile = os.getenv("MY_PERSONAL_PROFILE", "personal")

    if not access_key or not secret_key:
        raise ValueError(
            "Missing AWS credentials. Set MY_AWS_ACCESS_KEY_ID and MY_AWS_SECRET_ACCESS_KEY"
        )

    print(f"Using AWS profile: {profile}")

    return boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


def upload_file(s3_client, local_path: Path, s3_key: str) -> bool:
    """
    Upload a file to S3 with public-read access.
    """
    try:
        file_size_mb = local_path.stat().st_size / 1024 / 1024

        print(f"  Uploading {local_path.name} ({file_size_mb:.2f} MB)...")

        s3_client.upload_file(
            str(local_path),
            S3_BUCKET,
            s3_key,
            ExtraArgs={
                "ContentType": "application/geo+json",
                "CacheControl": "max-age=3600",
            },
        )

        url = f"https://{S3_BUCKET}/{s3_key}"
        print(f"  ✓ Uploaded to: {url}")
        return True

    except ClientError as e:
        print(f"  ✗ Upload failed: {e}")
        return False


def download_file(s3_client, s3_key: str, local_path: Path) -> bool:
    """
    Download a file from S3.
    """
    try:
        print(f"  Downloading {local_path.name}...")

        local_path.parent.mkdir(parents=True, exist_ok=True)

        s3_client.download_file(S3_BUCKET, s3_key, str(local_path))

        file_size_mb = local_path.stat().st_size / 1024 / 1024
        print(f"  ✓ Downloaded ({file_size_mb:.2f} MB)")
        return True

    except ClientError as e:
        print(f"  ✗ Download failed: {e}")
        return False


def upload_layers(layer_name: str = None, include_demographics: bool = True):
    """
    Upload one or all processed layers to S3.
    
    Args:
        layer_name: Specific layer to upload, or None for all
        include_demographics: Also upload demographics files if they exist
    """
    s3_client = get_s3_client()

    layers_to_upload = [layer_name] if layer_name else get_layers_from_config()

    print(f"\n{'='*60}")
    print(f"Uploading to S3: s3://{S3_BUCKET}/{S3_PREFIX}/")
    print(f"{'='*60}\n")

    success_count = 0
    fail_count = 0

    for layer in layers_to_upload:
        # Skip census config entry
        if layer == 'census':
            continue
            
        # Upload GeoJSON layer
        local_path = STANDARD_DIR / f"{layer}.geojson"

        if not local_path.exists():
            print(f"✗ {layer}: File not found at {local_path}")
            fail_count += 1
            continue

        s3_key = f"{S3_PREFIX}/{layer}.geojson"

        if upload_file(s3_client, local_path, s3_key):
            success_count += 1
        else:
            fail_count += 1

        print()
        
        # Upload demographics file if it exists and demographics are enabled
        if include_demographics:
            demo_path = STANDARD_DIR / f"{layer}_demographics.parquet"
            if demo_path.exists():
                demo_s3_key = f"{S3_PREFIX}/{layer}_demographics.parquet"
                if upload_file(s3_client, demo_path, demo_s3_key):
                    success_count += 1
                    print(f"  ✓ Also uploaded demographics")
                else:
                    fail_count += 1
                print()

    # Upload metadata
    upload_metadata(s3_client, include_demographics)

    print(f"{'='*60}")
    print(f"Upload complete: {success_count} succeeded, {fail_count} failed")
    print(f"{'='*60}\n")


def download_layers(layer_name: str = None, include_demographics: bool = True):
    """
    Download one or all processed layers from S3.
    
    Args:
        layer_name: Specific layer to download, or None for all
        include_demographics: Also download demographics files if they exist
    """
    s3_client = get_s3_client()

    layers_to_download = [layer_name] if layer_name else get_layers_from_config()

    print(f"\n{'='*60}")
    print(f"Downloading from S3: s3://{S3_BUCKET}/{S3_PREFIX}/")
    print(f"{'='*60}\n")

    success_count = 0
    fail_count = 0

    for layer in layers_to_download:
        # Skip census config entry
        if layer == 'census':
            continue
            
        # Download GeoJSON layer
        s3_key = f"{S3_PREFIX}/{layer}.geojson"
        local_path = STANDARD_DIR / f"{layer}.geojson"

        if download_file(s3_client, s3_key, local_path):
            success_count += 1
        else:
            fail_count += 1

        print()
        
        # Try to download demographics file if enabled
        if include_demographics:
            demo_s3_key = f"{S3_PREFIX}/{layer}_demographics.parquet"
            demo_path = STANDARD_DIR / f"{layer}_demographics.parquet"
            
            # Check if demographics file exists in S3
            try:
                s3_client.head_object(Bucket=S3_BUCKET, Key=demo_s3_key)
                # File exists, download it
                if download_file(s3_client, demo_s3_key, demo_path):
                    success_count += 1
                    print(f"  ✓ Also downloaded demographics")
                else:
                    fail_count += 1
                print()
            except ClientError:
                # Demographics file doesn't exist, skip silently
                pass

    print(f"{'='*60}")
    print(f"Download complete: {success_count} succeeded, {fail_count} failed")
    print(f"{'='*60}\n")


def upload_metadata(s3_client, include_demographics: bool = True):
    """
    Upload metadata JSON file with layer inventory and URLs.
    Automatically includes all layers from config/layers.yml.
    
    Args:
        s3_client: Boto3 S3 client
        include_demographics: Include demographics files in metadata
    """
    metadata = {
        "name": "LA Geography Boundaries",
        "description": "Clean, standardized boundary layers for Los Angeles",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "crs": "EPSG:4326",
        "base_url": f"https://{S3_BUCKET}/{S3_PREFIX}",
        "layers": {},
    }

    for layer in get_layers_from_config():
        # Skip census config entry
        if layer == 'census':
            continue
            
        local_path = STANDARD_DIR / f"{layer}.geojson"
        if local_path.exists():
            file_size_mb = local_path.stat().st_size / 1024 / 1024
            layer_info = {
                "url": f"https://{S3_BUCKET}/{S3_PREFIX}/{layer}.geojson",
                "size_mb": round(file_size_mb, 2),
            }
            
            # Add demographics info if file exists
            if include_demographics:
                demo_path = STANDARD_DIR / f"{layer}_demographics.parquet"
                if demo_path.exists():
                    demo_size_mb = demo_path.stat().st_size / 1024 / 1024
                    layer_info["demographics"] = {
                        "url": f"https://{S3_BUCKET}/{S3_PREFIX}/{layer}_demographics.parquet",
                        "size_mb": round(demo_size_mb, 2),
                        "source": "2020 Decennial Census",
                        "note": "Area-weighted apportionment from Census blocks"
                    }
            
            metadata["layers"][layer] = layer_info

    # Save locally
    metadata_path = STANDARD_DIR / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, indent=2, fp=f)

    # Upload to S3
    s3_key = f"{S3_PREFIX}/metadata.json"
    try:
        s3_client.upload_file(
            str(metadata_path),
            S3_BUCKET,
            s3_key,
            ExtraArgs={
                "ContentType": "application/json",
                "CacheControl": "max-age=300",
            },
        )
        print(f"✓ Uploaded metadata: https://{S3_BUCKET}/{s3_key}")
    except ClientError as e:
        print(f"✗ Metadata upload failed: {e}")


def list_layers():
    """
    List available layers in S3.
    """
    s3_client = get_s3_client()

    print(f"\n{'='*60}")
    print(f"S3 Layers: s3://{S3_BUCKET}/{S3_PREFIX}/")
    print(f"{'='*60}\n")

    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET, Prefix=f"{S3_PREFIX}/", Delimiter="/"
        )

        if "Contents" not in response:
            print("No layers found in S3")
            return

        for obj in response["Contents"]:
            key = obj["Key"]
            size_mb = obj["Size"] / 1024 / 1024
            modified = obj["LastModified"].strftime("%Y-%m-%d %H:%M:%S")

            filename = key.split("/")[-1]
            url = f"https://{S3_BUCKET}/{key}"

            print(f"{filename:40s} {size_mb:8.2f} MB  {modified}  {url}")

        print(f"\n{'='*60}\n")

    except ClientError as e:
        print(f"✗ List failed: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Upload/download LA geography layers to/from S3"
    )

    parser.add_argument(
        "action",
        choices=["upload", "download", "list"],
        help="Action to perform",
    )

    parser.add_argument(
        "--layer",
        help="Specific layer name (optional, defaults to all layers)",
    )
    
    parser.add_argument(
        "--no-demographics",
        action="store_true",
        help="Skip demographics files (only upload/download boundaries)",
    )

    args = parser.parse_args()
    
    include_demographics = not args.no_demographics

    try:
        if args.action == "upload":
            upload_layers(args.layer, include_demographics)
        elif args.action == "download":
            download_layers(args.layer, include_demographics)
        elif args.action == "list":
            list_layers()

    except NoCredentialsError:
        print("✗ AWS credentials not found. Check environment variables.")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

