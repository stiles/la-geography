#!/usr/bin/env python3
"""
Quick Census demographics statistics.

Display high-level stats for any layer's demographics data.
Useful for quick validation and exploration.

Usage:
    python scripts/census_stats.py lapd_divisions
    python scripts/census_stats.py la_city_neighborhoods --top 5
"""

import sys
from pathlib import Path

import pandas as pd

STANDARD_DIR = Path("data/standard")


def show_stats(layer_name: str, top_n: int = 3):
    """Show quick statistics for a layer."""
    demo_path = STANDARD_DIR / f"{layer_name}_demographics.parquet"
    
    if not demo_path.exists():
        print(f"✗ Demographics not found: {demo_path}")
        print(f"\nAvailable layers:")
        for p in sorted(STANDARD_DIR.glob("*_demographics.parquet")):
            print(f"  - {p.stem.replace('_demographics', '')}")
        return
    
    # Load data
    df = pd.read_parquet(demo_path)
    
    # Get ID column - ALWAYS prefer name/label fields over numeric IDs
    demo_cols = ['pop_total', 'pop_hispanic', 'housing_total']
    non_demo_cols = [c for c in df.columns if c not in demo_cols and not c.startswith('pop_') 
                     and not c.startswith('housing_') and not c.startswith('source_') 
                     and not c.startswith('apportioned_') and not c.startswith('census_')
                     and not c.startswith('statefp') and not c.startswith('countyfp')
                     and not c.startswith('tractce') and not c.startswith('blockce')
                     and not c.startswith('geoid') and not c.startswith('mtfcc')
                     and not c.startswith('ur') and not c.startswith('uace')
                     and not c.startswith('uatype') and not c.startswith('funcstat')
                     and not c.startswith('aland') and not c.startswith('awater')
                     and not c.startswith('intptlat') and not c.startswith('intptlon')
                     and not c.startswith('fetched_at') and not c.startswith('shape_')
                     and not c.endswith('20')]  # Exclude Census block metadata columns
    
    # Prefer name fields in this priority order
    name_field_priority = [
        'name',           # Generic name field
        'aprec',          # LAPD divisions
        'division',       # LAPD divisions (alternative)
        'bureau',         # LAPD bureaus
        'label',          # Generic label field
        'city_name',      # Cities
        'district_name',  # Council districts
        'stanum',         # Fire stations
    ]
    
    id_col = None
    for field in name_field_priority:
        if field in non_demo_cols:
            id_col = field
            break
    
    # If no name field found, use first non-demo column
    if id_col is None:
        id_col = non_demo_cols[0] if non_demo_cols else df.columns[0]
    
    print(f"\n{'='*70}")
    print(f"Demographics: {layer_name}")
    print(f"{'='*70}\n")
    
    # Overall stats
    print(f"Features: {len(df):,}")
    print(f"Total population: {df['pop_total'].sum():,.0f}")
    print(f"Total housing units: {df['housing_total'].sum():,.0f}")
    
    if 'housing_occupied' in df.columns:
        occ_rate = (df['housing_occupied'].sum() / df['housing_total'].sum()) * 100
        print(f"Occupancy rate: {occ_rate:.1f}%")
    
    # Demographics breakdown
    pop_total = df['pop_total'].sum()
    if pop_total > 0:
        print(f"\nRace/Ethnicity:")
        hispanic_pct = (df['pop_hispanic'].sum() / pop_total) * 100
        print(f"  Hispanic/Latino: {hispanic_pct:.1f}%")
        
        if 'pop_white_nh' in df.columns:
            white_pct = (df['pop_white_nh'].sum() / pop_total) * 100
            black_pct = (df['pop_black_nh'].sum() / pop_total) * 100
            asian_pct = (df['pop_asian_nh'].sum() / pop_total) * 100
            
            print(f"  White (non-Hispanic): {white_pct:.1f}%")
            print(f"  Black (non-Hispanic): {black_pct:.1f}%")
            print(f"  Asian (non-Hispanic): {asian_pct:.1f}%")
    
    # Top N by population
    if len(df) > 1:
        print(f"\nTop {top_n} by population:")
        top = df.nlargest(top_n, 'pop_total')[[id_col, 'pop_total']]
        for idx, row in top.iterrows():
            print(f"  {str(row[id_col]):30s} {row['pop_total']:>12,.0f}")
        
        # Bottom N by population
        print(f"\nBottom {top_n} by population:")
        bottom = df.nsmallest(top_n, 'pop_total')[[id_col, 'pop_total']]
        for idx, row in bottom.iterrows():
            print(f"  {str(row[id_col]):30s} {row['pop_total']:>12,.0f}")
        
        # Calculate and show diversity
        df['pct_hispanic'] = df['pop_hispanic'] / df['pop_total']
        if 'pop_white_nh' in df.columns:
            df['pct_white'] = df['pop_white_nh'] / df['pop_total']
            df['pct_black'] = df['pop_black_nh'] / df['pop_total']
            df['pct_asian'] = df['pop_asian_nh'] / df['pop_total']
            
            # Diversity index: 1 - sum of squared proportions (higher = more diverse)
            df['diversity'] = 1 - (
                df['pct_hispanic']**2 + df['pct_white']**2 + 
                df['pct_black']**2 + df['pct_asian']**2
            )
            
            print(f"\nMost diverse {top_n}:")
            most_diverse = df.nlargest(top_n, 'diversity')[[id_col, 'diversity']]
            for idx, row in most_diverse.iterrows():
                print(f"  {str(row[id_col]):30s} {row['diversity']:>12.3f}")
    
    # Metadata
    if 'apportioned_at' in df.columns:
        print(f"\nApportioned: {df['apportioned_at'].iloc[0]}")
    
    if 'source_blocks_count' in df.columns:
        total_blocks = df['source_blocks_count'].sum()
        avg_blocks = df['source_blocks_count'].mean()
        print(f"Census blocks: {total_blocks:,.0f} total, {avg_blocks:.0f} avg per feature")
    
    print(f"\n{'='*70}\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/census_stats.py LAYER_NAME [--top N]")
        print("\nExamples:")
        print("  python scripts/census_stats.py lapd_divisions")
        print("  python scripts/census_stats.py la_city_neighborhoods --top 10")
        print("\nAvailable layers:")
        for p in sorted(STANDARD_DIR.glob("*_demographics.parquet")):
            print(f"  - {p.stem.replace('_demographics', '')}")
        sys.exit(1)
    
    layer_name = sys.argv[1]
    
    # Parse --top argument
    top_n = 3
    if '--top' in sys.argv:
        top_idx = sys.argv.index('--top')
        if top_idx + 1 < len(sys.argv):
            try:
                top_n = int(sys.argv[top_idx + 1])
            except ValueError:
                pass
    
    show_stats(layer_name, top_n)


if __name__ == '__main__':
    main()

