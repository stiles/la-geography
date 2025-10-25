#!/usr/bin/env python3
"""
Fetch 2020 Census blocks and demographics for LA County.

Downloads Census block geometries from TIGER/Line shapefiles via pygris
and demographic data from the Census API. Combines and saves to data/census/.

Usage:
    python scripts/fetch_census.py
    python scripts/fetch_census.py --api-key YOUR_KEY

Census API key can be obtained free from:
https://api.census.gov/data/key_signup.html

API key can be provided via:
- Command line: --api-key YOUR_KEY
- Environment variable: CENSUS_API_KEY
- File: .census_api_key in project root
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

import geopandas as gpd
import pandas as pd
import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from geo_utils import ensure_wgs84, load_config


def get_api_key(args_key: str = None) -> str:
    """
    Get Census API key from various sources.
    
    Priority order:
    1. Command line argument
    2. Environment variable CENSUS_API_KEY
    3. File .census_api_key in project root
    
    Args:
        args_key: API key from command line
    
    Returns:
        API key string
    """
    # Check command line
    if args_key:
        return args_key
    
    # Check environment
    if 'CENSUS_API_KEY' in os.environ:
        return os.environ['CENSUS_API_KEY']
    
    # Check file
    key_file = Path('.census_api_key')
    if key_file.exists():
        return key_file.read_text().strip()
    
    print("\n⚠️  Census API key not found!")
    print("\nTo get a free API key:")
    print("  1. Visit: https://api.census.gov/data/key_signup.html")
    print("  2. Fill out the form and check your email")
    print("\nTo provide your API key:")
    print("  - Command line: python scripts/fetch_census.py --api-key YOUR_KEY")
    print("  - Environment: export CENSUS_API_KEY=YOUR_KEY")
    print("  - File: echo YOUR_KEY > .census_api_key")
    sys.exit(1)


def fetch_block_geometries(state_fips: str, county_fips: str, year: int = 2020) -> gpd.GeoDataFrame:
    """
    Fetch Census block geometries using pygris.
    
    Args:
        state_fips: State FIPS code (e.g., "06" for California)
        county_fips: County FIPS code (e.g., "037" for LA County)
        year: Census year (default 2020)
    
    Returns:
        GeoDataFrame with block geometries
    """
    try:
        import pygris
        from pygris import blocks
    except ImportError:
        print("\n⚠️  pygris not installed!")
        print("Install with: uv pip install pygris")
        sys.exit(1)
    
    print(f"\nFetching Census {year} block geometries...")
    print(f"  State: {state_fips} (California)")
    print(f"  County: {county_fips} (Los Angeles)")
    
    # Fetch blocks
    # pygris caches automatically to ~/Library/Caches/pygris (Mac) or ~/.cache/pygris (Linux)
    blocks_gdf = blocks(
        state=state_fips,
        county=county_fips,
        year=year,
        cache=True
    )
    
    # Standardize column names
    blocks_gdf.columns = blocks_gdf.columns.str.lower()
    
    # Ensure WGS84
    blocks_gdf = ensure_wgs84(blocks_gdf)
    
    # Create standard block GEOID if not present
    if 'geoid20' in blocks_gdf.columns:
        blocks_gdf['block_geoid'] = blocks_gdf['geoid20']
    elif 'geoid' in blocks_gdf.columns:
        blocks_gdf['block_geoid'] = blocks_gdf['geoid']
    else:
        # Build GEOID from components: STATE + COUNTY + TRACT + BLOCK
        blocks_gdf['block_geoid'] = (
            blocks_gdf['statefp20'].astype(str) +
            blocks_gdf['countyfp20'].astype(str) +
            blocks_gdf['tractce20'].astype(str) +
            blocks_gdf['blockce20'].astype(str)
        )
    
    print(f"  ✓ Fetched {len(blocks_gdf):,} blocks")
    
    return blocks_gdf


def fetch_census_data(
    state_fips: str,
    county_fips: str,
    variables: list,
    api_key: str,
    year: int = 2020
) -> pd.DataFrame:
    """
    Fetch Census demographic data from API.
    
    Args:
        state_fips: State FIPS code
        county_fips: County FIPS code
        variables: List of variable codes (e.g., ['P1_001N', 'P2_002N'])
        api_key: Census API key
        year: Census year (default 2020)
    
    Returns:
        DataFrame with demographic data indexed by block GEOID
    """
    try:
        from census import Census
    except ImportError:
        print("\n⚠️  census library not installed!")
        print("Install with: uv pip install census")
        sys.exit(1)
    
    print(f"\nFetching Census {year} demographic data...")
    print(f"  Variables: {len(variables)}")
    
    # Initialize Census client
    c = Census(api_key, year=year)
    
    # Fetch data for all blocks in county
    # Note: Census API uses PL dataset for redistricting data
    try:
        data = c.pl.get(
            variables,
            geo={
                'for': 'block:*',
                'in': f'state:{state_fips} county:{county_fips} tract:*'
            }
        )
    except Exception as e:
        print(f"\n⚠️  Census API error: {e}")
        print("\nTroubleshooting:")
        print("  - Check that your API key is valid")
        print("  - Verify network connection")
        print("  - Try again later (API may be temporarily unavailable)")
        sys.exit(1)
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Build block GEOID from geography components
    df['block_geoid'] = (
        df['state'].astype(str) +
        df['county'].astype(str) +
        df['tract'].astype(str) +
        df['block'].astype(str)
    )
    
    # Convert demographic columns to numeric
    for var in variables:
        if var in df.columns:
            df[var] = pd.to_numeric(df[var], errors='coerce').fillna(0)
    
    # Drop geography component columns, keep only GEOID and variables
    keep_cols = ['block_geoid'] + variables
    df = df[keep_cols]
    
    print(f"  ✓ Fetched data for {len(df):,} blocks")
    
    return df


def main():
    parser = argparse.ArgumentParser(
        description="Fetch 2020 Census blocks and demographics for LA County"
    )
    parser.add_argument(
        '--api-key',
        help='Census API key (or set CENSUS_API_KEY env var)'
    )
    parser.add_argument(
        '--config',
        default='config/layers.yml',
        help='Path to configuration file (default: config/layers.yml)'
    )
    parser.add_argument(
        '--out-dir',
        default='data/census',
        help='Output directory (default: data/census)'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    print("=" * 70)
    print("Census Data Fetch - LA County 2020")
    print("=" * 70)
    
    config = load_config(args.config)
    census_config = config.get('census', {})
    
    state_fips = census_config.get('state_fips', '06')
    county_fips = census_config.get('county_fips', '037')
    vintage = census_config.get('vintage', 2020)
    
    # Get API key
    api_key = get_api_key(args.api_key)
    print(f"  ✓ Census API key loaded (ending in ...{api_key[-4:]})")
    
    # Extract variables from config
    variables = []
    tables = census_config.get('tables', {})
    for table_name, table_info in tables.items():
        table_vars = table_info.get('variables', {})
        variables.extend(table_vars.keys())
    
    print(f"\nConfiguration:")
    print(f"  Vintage: {vintage}")
    print(f"  State: {state_fips} (California)")
    print(f"  County: {county_fips} (Los Angeles)")
    print(f"  Variables: {len(variables)}")
    
    # Create output directories
    out_dir = Path(args.out_dir)
    raw_dir = out_dir / 'raw'
    processed_dir = out_dir / 'processed'
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Fetch block geometries
    blocks_geom = fetch_block_geometries(state_fips, county_fips, vintage)
    
    # Fetch demographic data
    blocks_demo = fetch_census_data(state_fips, county_fips, variables, api_key, vintage)
    
    # Join geometries and demographics
    print("\nJoining geometries and demographics...")
    blocks_enriched = blocks_geom.merge(
        blocks_demo,
        on='block_geoid',
        how='left'
    )
    
    # Fill missing demographic values with 0
    for var in variables:
        if var in blocks_enriched.columns:
            blocks_enriched[var] = blocks_enriched[var].fillna(0)
    
    # Apply column name mapping from config
    column_mapping = census_config.get('column_mapping', {})
    rename_map = {k: v for k, v in column_mapping.items() if k in blocks_enriched.columns}
    blocks_enriched = blocks_enriched.rename(columns=rename_map)
    
    # Add metadata
    blocks_enriched['fetched_at'] = datetime.now().isoformat()
    blocks_enriched['census_vintage'] = vintage
    
    print(f"  ✓ Joined data: {len(blocks_enriched):,} blocks")
    
    # Save raw geometries (GeoJSON)
    print("\nSaving outputs...")
    geom_path = raw_dir / 'blocks_2020_geometries.geojson'
    blocks_geom.to_file(geom_path, driver='GeoJSON')
    print(f"  ✓ Saved geometries: {geom_path}")
    
    # Save raw demographics (Parquet - no geometry)
    demo_path = raw_dir / 'blocks_2020_demographics.parquet'
    blocks_demo.to_parquet(demo_path)
    print(f"  ✓ Saved demographics: {demo_path}")
    
    # Save enriched blocks (Parquet with geometry)
    enriched_path = processed_dir / 'blocks_2020_enriched.parquet'
    blocks_enriched.to_parquet(enriched_path)
    print(f"  ✓ Saved enriched blocks: {enriched_path}")
    
    # Print summary statistics
    print("\n" + "=" * 70)
    print("Summary Statistics")
    print("=" * 70)
    
    # Get renamed column names
    pop_col = column_mapping.get('P1_001N', 'P1_001N')
    hispanic_col = column_mapping.get('P2_002N', 'P2_002N')
    housing_col = column_mapping.get('H1_001N', 'H1_001N')
    
    if pop_col in blocks_enriched.columns:
        total_pop = blocks_enriched[pop_col].sum()
        print(f"Total population: {total_pop:,.0f}")
    
    if hispanic_col in blocks_enriched.columns:
        total_hispanic = blocks_enriched[hispanic_col].sum()
        print(f"Hispanic/Latino: {total_hispanic:,.0f}")
    
    if housing_col in blocks_enriched.columns:
        total_housing = blocks_enriched[housing_col].sum()
        print(f"Housing units: {total_housing:,.0f}")
    
    print("\n✓ Census data fetch complete!")
    print(f"\nNext steps:")
    print(f"  1. Review the data in {enriched_path}")
    print(f"  2. Run apportionment: make apportion-census")
    print("=" * 70)


if __name__ == '__main__':
    main()

