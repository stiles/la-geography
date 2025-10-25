#!/usr/bin/env python3
"""
Analyze Census demographics across LA geography layers.

Showcases demographic data quality, calculates interesting statistics,
and validates apportionment results. Useful for testing and demonstration.

Usage:
    python scripts/analyze_demographics.py
    python scripts/analyze_demographics.py --layer lapd_divisions
    python scripts/analyze_demographics.py --save-report
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import geopandas as gpd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from geo_utils import load_config

STANDARD_DIR = Path("data/standard")


def format_pct(value, decimals=1):
    """Format percentage value."""
    return f"{value:.{decimals}f}%"


def format_number(value):
    """Format number with commas."""
    return f"{value:,.0f}"


def analyze_layer(layer_name: str, config: dict) -> dict:
    """
    Analyze demographics for a single layer.
    
    Args:
        layer_name: Name of the layer
        config: Configuration dictionary
    
    Returns:
        Dictionary with analysis results
    """
    print("\n" + "=" * 70)
    print(f"Analyzing: {layer_name}")
    print("=" * 70)
    
    # Load boundaries and demographics
    boundary_path = STANDARD_DIR / f"{layer_name}.geojson"
    demo_path = STANDARD_DIR / f"{layer_name}_demographics.parquet"
    
    if not boundary_path.exists():
        print(f"  ✗ Boundary file not found: {boundary_path}")
        return None
    
    if not demo_path.exists():
        print(f"  ✗ Demographics file not found: {demo_path}")
        return None
    
    # Load data
    boundaries = gpd.read_file(boundary_path)
    demographics = pd.read_parquet(demo_path)
    
    # Get layer ID field - but ALWAYS prefer name fields over numeric IDs
    demo_cols = [c for c in demographics.columns if c.startswith('pop_') or 
                 c.startswith('housing_') or c.startswith('source_') or 
                 c.startswith('apportioned_') or c.startswith('census_')
                 or c.startswith('statefp') or c.startswith('countyfp')
                 or c.startswith('tractce') or c.startswith('blockce')
                 or c.startswith('geoid') or c.startswith('mtfcc')
                 or c.startswith('ur') or c.startswith('uace')
                 or c.startswith('uatype') or c.startswith('funcstat')
                 or c.startswith('aland') or c.startswith('awater')
                 or c.startswith('intptlat') or c.startswith('intptlon')
                 or c.startswith('fetched_at') or c.startswith('shape_')
                 or c.startswith('P2_') or c.startswith('H1_')
                 or c.endswith('20')]  # Exclude Census block metadata
    non_demo_cols = [c for c in demographics.columns if c not in demo_cols]
    
    # Prefer name fields in this priority order (even if id_field is set)
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
    
    id_field = None
    for field in name_field_priority:
        if field in non_demo_cols:
            id_field = field
            break
    
    # If no name field found, fall back to config id_field or first column
    if id_field is None:
        layer_config = config.get(layer_name, {})
        id_field = layer_config.get('id_field')
        if id_field is None or id_field == 'null' or id_field not in demographics.columns:
            id_field = non_demo_cols[0] if non_demo_cols else demographics.columns[0]
    
    # Join
    if id_field in boundaries.columns and id_field in demographics.columns:
        data = boundaries.merge(demographics, on=id_field, how='inner')
    else:
        # Fallback: just use demographics
        data = demographics.copy()
    
    print(f"\n  Features: {len(data):,}")
    
    # Calculate total statistics
    totals = {
        'pop_total': data['pop_total'].sum(),
        'pop_hispanic': data['pop_hispanic'].sum(),
        'pop_white_nh': data['pop_white_nh'].sum(),
        'pop_black_nh': data['pop_black_nh'].sum(),
        'pop_asian_nh': data['pop_asian_nh'].sum(),
        'housing_total': data['housing_total'].sum(),
        'housing_occupied': data['housing_occupied'].sum(),
    }
    
    print(f"  Total population: {format_number(totals['pop_total'])}")
    print(f"  Total housing units: {format_number(totals['housing_total'])}")
    
    # Calculate percentages
    if totals['pop_total'] > 0:
        pct_hispanic = (totals['pop_hispanic'] / totals['pop_total']) * 100
        pct_white = (totals['pop_white_nh'] / totals['pop_total']) * 100
        pct_black = (totals['pop_black_nh'] / totals['pop_total']) * 100
        pct_asian = (totals['pop_asian_nh'] / totals['pop_total']) * 100
        
        print(f"\n  Demographics:")
        print(f"    Hispanic/Latino: {format_pct(pct_hispanic)}")
        print(f"    White (non-Hispanic): {format_pct(pct_white)}")
        print(f"    Black (non-Hispanic): {format_pct(pct_black)}")
        print(f"    Asian (non-Hispanic): {format_pct(pct_asian)}")
    
    if totals['housing_total'] > 0:
        occupancy_rate = (totals['housing_occupied'] / totals['housing_total']) * 100
        print(f"\n  Housing occupancy rate: {format_pct(occupancy_rate)}")
    
    # Find superlatives (if multiple features)
    if len(data) > 1 and id_field in data.columns:
        print(f"\n  Superlatives:")
        
        # Most populous
        most_pop = data.nlargest(1, 'pop_total')[[id_field, 'pop_total']].iloc[0]
        print(f"    Most populous: {most_pop[id_field]} ({format_number(most_pop['pop_total'])} people)")
        
        # Least populous
        least_pop = data.nsmallest(1, 'pop_total')[[id_field, 'pop_total']].iloc[0]
        print(f"    Least populous: {least_pop[id_field]} ({format_number(least_pop['pop_total'])} people)")
        
        # Calculate diversity index (higher = more diverse)
        # Using simplified diversity: 1 - sum of squared proportions
        data['pct_hispanic'] = data['pop_hispanic'] / data['pop_total']
        data['pct_white_nh'] = data['pop_white_nh'] / data['pop_total']
        data['pct_black_nh'] = data['pop_black_nh'] / data['pop_total']
        data['pct_asian_nh'] = data['pop_asian_nh'] / data['pop_total']
        
        data['diversity_index'] = 1 - (
            data['pct_hispanic']**2 + 
            data['pct_white_nh']**2 + 
            data['pct_black_nh']**2 + 
            data['pct_asian_nh']**2
        )
        
        most_diverse = data.nlargest(1, 'diversity_index')[[id_field, 'diversity_index']].iloc[0]
        print(f"    Most diverse: {most_diverse[id_field]} (index: {most_diverse['diversity_index']:.3f})")
        
        # Highest Hispanic percentage
        data['pct_hispanic_display'] = data['pct_hispanic'] * 100
        highest_hispanic = data.nlargest(1, 'pct_hispanic')[[id_field, 'pct_hispanic_display']].iloc[0]
        print(f"    Highest % Hispanic: {highest_hispanic[id_field]} ({format_pct(highest_hispanic['pct_hispanic_display'])})")
        
        # Calculate area if available
        if 'area_sqmi' in data.columns:
            data['density'] = data['pop_total'] / data['area_sqmi']
            highest_density = data.nlargest(1, 'density')[[id_field, 'density']].iloc[0]
            print(f"    Highest density: {highest_density[id_field]} ({format_number(highest_density['density'])} per sq mi)")
    
    return {
        'layer': layer_name,
        'features': len(data),
        'totals': totals,
        'success': True
    }


def compare_layers(config: dict):
    """
    Compare demographics across different layer types.
    """
    print("\n" + "=" * 70)
    print("Cross-Layer Comparison")
    print("=" * 70)
    
    # Define interesting comparisons
    comparisons = [
        {
            'name': 'LA City vs LA County',
            'layers': ['la_city_boundary', 'la_county_boundary']
        },
        {
            'name': 'LAPD Bureaus',
            'layers': ['lapd_bureaus']
        },
        {
            'name': 'Major Jurisdictions',
            'layers': ['la_city_boundary', 'la_county_boundary']
        }
    ]
    
    # Load and compare
    for comp in comparisons:
        print(f"\n{comp['name']}:")
        print("-" * 60)
        
        for layer in comp['layers']:
            demo_path = STANDARD_DIR / f"{layer}_demographics.parquet"
            if demo_path.exists():
                demo = pd.read_parquet(demo_path)
                pop = demo['pop_total'].sum()
                hispanic_pct = (demo['pop_hispanic'].sum() / pop * 100) if pop > 0 else 0
                print(f"  {layer:40s} {format_number(pop):>15s}  ({format_pct(hispanic_pct)} Hispanic)")


def generate_report(config: dict, output_path: Path):
    """
    Generate a markdown report of all demographics.
    """
    print("\n" + "=" * 70)
    print("Generating Demographics Report")
    print("=" * 70)
    
    report = []
    report.append("# LA Geography Demographics Report")
    report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("\n## Summary Statistics\n")
    
    # Get all polygon layers
    polygon_layers = []
    for layer_name, layer_config in config.items():
        if layer_name == 'census':
            continue
        if isinstance(layer_config, dict):
            geom_type = layer_config.get('geometry_type', '')
            if geom_type == 'polygon':
                demo_path = STANDARD_DIR / f"{layer_name}_demographics.parquet"
                if demo_path.exists():
                    polygon_layers.append(layer_name)
    
    report.append(f"**Layers with demographics:** {len(polygon_layers)}\n")
    
    # Create summary table
    report.append("| Layer | Features | Population | % Hispanic | Housing Units |")
    report.append("|-------|----------|------------|------------|---------------|")
    
    for layer in sorted(polygon_layers):
        demo_path = STANDARD_DIR / f"{layer}_demographics.parquet"
        demo = pd.read_parquet(demo_path)
        
        features = len(demo)
        pop = demo['pop_total'].sum()
        hispanic_pct = (demo['pop_hispanic'].sum() / pop * 100) if pop > 0 else 0
        housing = demo['housing_total'].sum()
        
        report.append(
            f"| `{layer}` | {features:,} | {pop:,.0f} | {hispanic_pct:.1f}% | {housing:,.0f} |"
        )
    
    # Key findings
    report.append("\n## Key Findings\n")
    
    # LA County totals
    county_path = STANDARD_DIR / "la_county_boundary_demographics.parquet"
    if county_path.exists():
        county = pd.read_parquet(county_path)
        pop = county['pop_total'].sum()
        report.append(f"- **LA County Total Population:** {pop:,.0f}")
        hispanic_pct = (county['pop_hispanic'].sum() / pop * 100)
        report.append(f"- **LA County % Hispanic/Latino:** {hispanic_pct:.1f}%")
    
    # LA City totals
    city_path = STANDARD_DIR / "la_city_boundary_demographics.parquet"
    if city_path.exists():
        city = pd.read_parquet(city_path)
        pop = city['pop_total'].sum()
        report.append(f"- **LA City Total Population:** {pop:,.0f}")
        hispanic_pct = (city['pop_hispanic'].sum() / pop * 100)
        report.append(f"- **LA City % Hispanic/Latino:** {hispanic_pct:.1f}%")
    
    report.append("\n---\n")
    report.append("*Data source: 2020 Decennial Census (PL 94-171)*")
    
    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write('\n'.join(report))
    
    print(f"\n  ✓ Report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Census demographics across LA geography layers"
    )
    parser.add_argument(
        '--layer',
        help='Analyze specific layer (default: analyze all)'
    )
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Compare demographics across layers'
    )
    parser.add_argument(
        '--save-report',
        action='store_true',
        help='Generate markdown report'
    )
    parser.add_argument(
        '--config',
        default='config/layers.yml',
        help='Path to configuration file (default: config/layers.yml)'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    print("=" * 70)
    print("Census Demographics Analysis")
    print("=" * 70)
    
    if args.layer:
        # Analyze single layer
        analyze_layer(args.layer, config)
    else:
        # Analyze all polygon layers with demographics
        results = []
        for layer_name, layer_config in config.items():
            if layer_name == 'census':
                continue
            
            if isinstance(layer_config, dict):
                geom_type = layer_config.get('geometry_type', '')
                if geom_type == 'polygon':
                    demo_path = STANDARD_DIR / f"{layer_name}_demographics.parquet"
                    if demo_path.exists():
                        result = analyze_layer(layer_name, config)
                        if result:
                            results.append(result)
        
        # Summary
        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)
        print(f"\nAnalyzed {len(results)} polygon layers with demographics")
        
        # Calculate grand totals
        total_pop = sum(r['totals']['pop_total'] for r in results if r)
        print(f"Combined population across all layers: {format_number(total_pop)}")
        print("(Note: Overlapping layers will have duplicate counts)")
    
    if args.compare:
        compare_layers(config)
    
    if args.save_report:
        report_path = Path("data/docs/DEMOGRAPHICS_REPORT.md")
        generate_report(config, report_path)
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()

