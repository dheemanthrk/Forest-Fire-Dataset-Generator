#!/usr/bin/env python3
# climate.py

import os
import sys
import argparse
from datetime import datetime
import cdsapi
import geopandas as gpd
import xarray as xr
import pandas as pd

def parse_arguments():
    """
    Parse command-line arguments specific to climate data processing.
    """
    parser = argparse.ArgumentParser(description="Climate Data Processing")
    parser.add_argument(
        "--province",
        type=str,
        required=True,
        help="Name of the province"
    )
    parser.add_argument(
        "--start_date",
        type=str,
        required=True,
        help="Start date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--end_date",
        type=str,
        required=True,
        help="End date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="Directory to save processed climate data"
    )
    return parser.parse_args()

def get_bounding_box(shapefile_path):
    """
    Calculate the bounding box (north, west, south, east) from a shapefile.
    """
    shapefile = gpd.read_file(shapefile_path)

    # Ensure CRS is EPSG:4326
    if shapefile.crs.to_epsg() != 4326:
        shapefile = shapefile.to_crs("EPSG:4326")
    bounds = shapefile.total_bounds  # [west, south, east, north]
    bbox = [bounds[3], bounds[0], bounds[1], bounds[2]]  # [north, west, south, east]
    print(f"Bounding Box: {bbox}")
    return bbox

def fetch_climate_data(bbox, year, months, output_dir):
    """
    Fetch climate data using CDS API.
    """
    print("Starting data fetch from CDS API...")
    c = cdsapi.Client()
    for month in months:
        filename = f"climate_data_{year}_{month:02d}.nc"
        filepath = os.path.join(output_dir, filename)
        print(f"Fetching data for {year}-{month:02d}...")
        try:
            c.retrieve(
                'reanalysis-era5-single-levels',
                {
                    'product_type': 'reanalysis',
                    'variable': [
                        '2m_temperature'
                        # '2m_temperature', 'total_precipitation', '10m_u_component_of_wind',
                        # '10m_v_component_of_wind', '2m_dewpoint_temperature',
                        # 'surface_solar_radiation_downwards', 'volumetric_soil_water_layer_1',
                    ],
                    'year': str(year),
                    'month': f"{month:02d}",
                    'day': [f"{day:02d}" for day in range(1, 32)],
                    'time': '12:00',
                    'area': bbox,  # north, west, south, east
                    'format': 'netcdf',
                },
                filepath)
            print(f"Climate data saved to {filepath}.")
        except Exception as e:
            print(f"Error fetching climate data for {year}-{month:02d}: {e}")
            sys.exit(1)

def convert_nc_to_csv(nc_file, csv_file, variables):
    """
    Convert NetCDF file to CSV for specified variables.
    """
    print(f"Converting {nc_file} to {csv_file}...")
    try:
        ds = xr.open_dataset(nc_file)
        data = ds[variables].to_dataframe().reset_index()
        data.to_csv(csv_file, index=False)
        print(f"Conversion completed: {csv_file}")
    except Exception as e:
        print(f"Error converting {nc_file} to CSV: {e}")
        sys.exit(1)

def map_to_grid(csv_file, shapefile_path, mapped_file):
    """
    Map climate data to the grid defined by the shapefile.
    Placeholder for actual spatial mapping logic.
    """
    print(f"Mapping {csv_file} to grid defined by {shapefile_path}...")
    try:
        # Load climate data
        climate_df = pd.read_csv(csv_file)

        # Load shapefile
        shapefile = gpd.read_file(shapefile_path)

        # Placeholder: Implement actual mapping logic here
        # For demonstration, we'll assume that the mapping is a simple aggregation or spatial join
        # Replace this with your actual mapping logic as needed

        # Example: Save the original data as mapped data (to be replaced)
        climate_df.to_csv(mapped_file, index=False)
        print(f"Mapped data saved to {mapped_file}")
    except Exception as e:
        print(f"Error mapping data to grid: {e}")
        sys.exit(1)

def process_climate_data(province, start_date, end_date, output_dir):
    """
    Main function to process climate data.
    """
    # Parse dates
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        print("Error: Dates must be in YYYY-MM-DD format.")
        sys.exit(1)

    if start_dt > end_dt:
        print("Error: Start date must be before or equal to end date.")
        sys.exit(1)

    # Determine years and months to process
    years_months = []
    current_year = start_dt.year
    current_month = start_dt.month
    while (current_year < end_dt.year) or (current_year == end_dt.year and current_month <= end_dt.month):
        years_months.append((current_year, current_month))
        if current_month == 12:
            current_month = 1
            current_year += 1
        else:
            current_month += 1

    # Shapefile path
    shapefile_dir = os.path.join("Data", "grid", province)
    shapefile_path = os.path.join(shapefile_dir, f"{province.lower()}_grid.shp")
    
    if not os.path.exists(shapefile_path):
        print(f"Error: Shapefile for province '{province}' not found at {shapefile_path}.")
        sys.exit(1)

    # Get bounding box
    bbox = get_bounding_box(shapefile_path)

    for year, month in years_months:
        print(f"\n--- Processing {year}-{month:02d} ---")

        # Define file paths
        nc_file = os.path.join(output_dir, f"climate_data_{year}_{month:02d}.nc")
        csv_file = os.path.join(output_dir, f"climate_data_{year}_{month:02d}.csv")
        mapped_file = os.path.join(output_dir, f"mapped_climate_data_{year}_{month:02d}.csv")

        # Fetch Climate Data
        fetch_climate_data(bbox, year, [month], output_dir)

        # Convert NetCDF to CSV
        variables = [
            "t2m",    # 2 metre temperature
            "tp",     # Total precipitation
            "u10",    # 10 metre U wind component
            "v10",    # 10 metre V wind component
            "d2m",    # 2 metre dewpoint temperature
            "ssrd",   # Surface short-wave (solar) radiation
            "swvl1"   # Volumetric soil water layer 1
        ]
        convert_nc_to_csv(nc_file, csv_file, variables)

        # Map to Grid
        map_to_grid(csv_file, shapefile_path, mapped_file)

    print("\nClimate data processing completed.")

def main():
    args = parse_arguments()

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    process_climate_data(
        province=args.province,
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir
    )

if __name__ == "__main__":
    main()
