import os
import cdsapi
import numpy as np
import geopandas as gpd
import pandas as pd
import xarray as xr
import zipfile
import shutil
import glob
from shapely.geometry import Point
from datetime import datetime

def process_climate_data(province, start_date, end_date, base_output_dir):
    """
    Fetch, process, and map climate data for a given province within a date range.
    
    Steps:
    1. Get bounding box from province shapefile.
    2. Fetch climate data from CDS API.
    3. Extract NetCDF from ZIP and convert to CSV.
    4. Map and aggregate climate data to grid.
    
    Args:
        province (str): Name of the province.
        start_date (str): Start date in YYYY-MM-DD format.
        end_date (str): End date in YYYY-MM-DD format.
        base_output_dir (str): Base directory for storing output files.
    """
    
    # 1️⃣ **Get Bounding Box**
    shapefile_path = f"Data/Grid/{province}/{province.replace(' ', '_')}_Grid.shp"
    
    if not os.path.exists(shapefile_path):
        raise FileNotFoundError(f"Shapefile not found: {shapefile_path}")

    def get_bounding_box_cds(shapefile_path):
        gdf = gpd.read_file(shapefile_path)
        if gdf.crs is None or gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")
        bounds = gdf.total_bounds
        return [bounds[3], bounds[0], bounds[1], bounds[2]]  # [North, West, South, East]

    bbox_cds = get_bounding_box_cds(shapefile_path)
    print(f"CDS Bounding Box for {province}: {bbox_cds}")

    # 2️⃣ **Prepare Request ID & Output Paths**
    request_dir = os.path.join(base_output_dir, "Climate")
    os.makedirs(request_dir, exist_ok=True)

    zip_file = os.path.join(request_dir, "climate_data.zip")
    nc_file = os.path.join(request_dir, "climate_data.nc")
    csv_file = os.path.join(request_dir, "climate_data.csv")
    output_csv = os.path.join(request_dir, "aggregated_climate_data.csv")

    # 3️⃣ **Fetch Climate Data**
    c = cdsapi.Client()

    request_params = {
        'product_type': 'reanalysis',
        "data_format": "netcdf",
        "download_format": "zip",
        'variable': [
            "10m_u_component_of_wind",
            "10m_v_component_of_wind",
            "2m_dewpoint_temperature",
            "2m_temperature",
            "surface_pressure",
            "total_precipitation",
        ],
        'year': start_date[:4],  # Extract year from start_date
        'month': start_date[5:7],  # Extract month
        'day': [f"{day:02d}" for day in range(1, 32)],
        'time': '12:00',
        'area': [np.float64(coord) for coord in bbox_cds],  # North, West, South, East
    }

    print("Fetching climate data from CDS API...")
    c.retrieve('reanalysis-era5-land', request_params, zip_file)
    print(f"✅ Data downloaded successfully: {zip_file}")

    # 4️⃣ **Extract & Convert NetCDF to CSV**
    def process_zip(zip_file, output_csv):
        temp_dir = os.path.join(request_dir, "temp_extracted")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)

        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        nc_files = glob.glob(os.path.join(temp_dir, "*.nc"))
        if not nc_files:
            raise FileNotFoundError("No NetCDF (.nc) files found in the ZIP archive.")

        extracted_nc_file = nc_files[0]
        print(f"Found NetCDF file: {extracted_nc_file}")

        def convert_nc_to_csv(nc_file, csv_file):
            ds = xr.open_dataset(nc_file)
            data = ds.to_dataframe().reset_index()
            data.to_csv(csv_file, index=False)
            print(f"Conversion completed: {csv_file}")

        convert_nc_to_csv(extracted_nc_file, output_csv)
        shutil.rmtree(temp_dir)  # Cleanup

    process_zip(zip_file, csv_file)

    # 5️⃣ **Map & Aggregate Data to Grid**
    def map_and_aggregate_points_to_grid(csv_file, shapefile_path, output_csv):
        df = pd.read_csv(csv_file)

        if 'latitude' not in df.columns or 'longitude' not in df.columns or 'valid_time' not in df.columns:
            raise ValueError("CSV must contain 'latitude', 'longitude', and 'valid_time' columns")

        df['valid_time'] = pd.to_datetime(df['valid_time']).dt.date

        df = df.rename(columns={
            'valid_time': 'Date',
            't2m': 'Temperature_2m_C',
            'tp': 'Total_Precip_mm',
            'u10': 'Wind_Speed_U_10m',
            'v10': 'Wind_Speed_V_10m',
            'd2m': 'Dew_Point_2m_C',
            'sp': 'Surface_Pressure_Pa'
        })

        df['geometry'] = df.apply(lambda row: Point(row['longitude'], row['latitude']), axis=1)
        points_gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")

        grid_gdf = gpd.read_file(shapefile_path)
        if grid_gdf.crs is None or grid_gdf.crs.to_epsg() != 4326:
            grid_gdf = grid_gdf.to_crs("EPSG:4326")

        projected_gdf = grid_gdf.to_crs("EPSG:3857")
        projected_gdf['centroid'] = projected_gdf.geometry.centroid
        grid_gdf['centroid'] = projected_gdf['centroid'].to_crs("EPSG:4326")

        mapped_gdf = gpd.sjoin(points_gdf, grid_gdf, how="inner", predicate="within")

        mapped_gdf = mapped_gdf.rename(columns={'grid_id': 'GridID'})
        mapped_gdf = mapped_gdf.drop(columns=['index_right'], errors='ignore')

        aggregated_gdf = mapped_gdf.groupby(['GridID', 'Date']).agg({
            'Wind_Speed_U_10m': 'mean',
            'Wind_Speed_V_10m': 'mean',
            'Dew_Point_2m_C': 'mean',
            'Temperature_2m_C': 'mean',
            'Surface_Pressure_Pa': 'mean',
            'Total_Precip_mm': 'mean'
        }).reset_index()

        centroids = grid_gdf[['grid_id', 'centroid']]
        aggregated_gdf = pd.merge(aggregated_gdf, centroids, left_on='GridID', right_on='grid_id')
        aggregated_gdf = aggregated_gdf.drop(columns=['grid_id'])

        aggregated_gdf['Latitude'] = aggregated_gdf['centroid'].apply(lambda point: point.y)
        aggregated_gdf['Longitude'] = aggregated_gdf['centroid'].apply(lambda point: point.x)
        aggregated_gdf = aggregated_gdf.drop(columns=['centroid'])

        aggregated_gdf.to_csv(output_csv, index=False)
        print(f"✅ Final output saved: {output_csv}")

    map_and_aggregate_points_to_grid(csv_file, shapefile_path, output_csv)

    print(f"🎯 Process completed. Output stored in {request_dir}")

# # **Example Usage**
# process_climate_data(
#     province="Alberta",
#     start_date="2022-04-01",
#     end_date="2022-04-30"
# )
