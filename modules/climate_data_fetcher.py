# modules/climate_data_fetcher.py

import os
import cdsapi
import pandas as pd
from datetime import datetime, timedelta
import geopandas as gpd
from shapely.geometry import Point

def fetch_climate_data(bounding_box, start_date, end_date, output_folder):
    """
    Fetches climate data from CDS API, converts NetCDF to CSV, maps to grid IDs,
    and aggregates data per grid centroid.
    
    Parameters:
    - bounding_box (list): [minx, miny, maxx, maxy]
    - start_date (str): Start date in YYYY-MM-DD
    - end_date (str): End date in YYYY-MM-DD
    - output_folder (str): Directory to save the CSV
    """
    try:
        os.makedirs(output_folder, exist_ok=True)
        
        c = cdsapi.Client()
        
        # Define the variables to fetch
        variables = [
            '2m_temperature',      # Temperature
            'total_precipitation', # Precipitation
            '2m_dewpoint_temperature', # Humidity (approximated via dew point)
            '10m_u_component_of_wind', # Wind Speed (U)
            '10m_v_component_of_wind', # Wind Speed (V)
            'soil_temperature_level_1', # Soil Top Layer
        ]
        
        # Fetch data
        print("[climate_data_fetcher.py] Starting climate data fetch from CDS API...")
        c.retrieve(
            'reanalysis-era5-single-levels',
            {
                'product_type': 'reanalysis',
                'format': 'netcdf',
                'variable': variables,
                'year': start_date.split('-')[0],
                'month': [f"{i:02d}" for i in range(int(start_date.split('-')[1]), int(end_date.split('-')[1]) + 1)],
                'day': [f"{i:02d}" for i in range(1, 32)],
                'time': '12:00',  # Daily average at 12:00 UTC
                'area': [
                    bounding_box[3],  # North
                    bounding_box[0],  # West
                    bounding_box[1],  # South
                    bounding_box[2],  # East
                ],
            },
            os.path.join(output_folder, 'climate_data.nc')
        )
        print("[climate_data_fetcher.py] Climate data fetched successfully.")
        
        # Convert NetCDF to CSV
        print("[climate_data_fetcher.py] Converting NetCDF to CSV...")
        df = netcdf_to_dataframe(os.path.join(output_folder, 'climate_data.nc'))
        df.to_csv(os.path.join(output_folder, 'climate_data_raw.csv'), index=False)
        print("[climate_data_fetcher.py] Conversion complete. Raw CSV saved.")
        
        # Map to Grid IDs and Aggregate
        print("[climate_data_fetcher.py] Mapping data to grid IDs and aggregating...")
        grid_shapefile = os.path.join(output_folder, '..', '..', 'data', 'grid', 'Ontario', 'Ontario_Grid.shp')  # Adjust path as needed
        final_csv = os.path.join(output_folder, 'climate_data.csv')
        map_and_aggregate(df, grid_shapefile, final_csv)
        print(f"[climate_data_fetcher.py] Final aggregated climate data saved to {final_csv}.")
    
        def netcdf_to_dataframe(nc_file):
            """
            Converts a NetCDF file to a pandas DataFrame.
            """
            import xarray as xr
            
            ds = xr.open_dataset(nc_file)
            df = ds.to_dataframe().reset_index()
            
            # Convert temperature from Kelvin to Celsius
            if 't2m' in df.columns:
                df['t2m'] = df['t2m'] - 273.15
            if 'd2m' in df.columns:
                df['d2m'] = df['d2m'] - 273.15
            
            # Calculate wind speed from u and v components
            if 'u10' in df.columns and 'v10' in df.columns:
                df['wind_speed'] = (df['u10']**2 + df['v10']**2)**0.5
            
            # Rename columns for clarity
            df.rename(columns={
                't2m': 'temperature',
                'total_precipitation': 'precipitation',
                'd2m': 'dewpoint',
                'wind_speed': 'wind_speed',
                'soil_temperature_level_1': 'soil_temp_top_layer'
            }, inplace=True)
            
            # Select relevant columns
            df = df[['time', 'latitude', 'longitude', 'temperature', 'precipitation', 'dewpoint', 'wind_speed', 'soil_temp_top_layer']]
            
            # Rename 'time' to 'date'
            df.rename(columns={'time': 'date'}, inplace=True)
            
            return df
        
        def map_and_aggregate(df, grid_shapefile, final_csv):
            """
            Maps lat/long to grid IDs, aggregates data per grid centroid.
            """
            # Load grid shapefile
            grid_gdf = gpd.read_file(grid_shapefile)
            grid_gdf = grid_gdf.to_crs("EPSG:4326")  # Ensure it's in lat/lon
            
            # Create GeoDataFrame from climate data
            climate_gdf = gpd.GeoDataFrame(
                df,
                geometry=gpd.points_from_xy(df.longitude, df.latitude),
                crs="EPSG:4326"
            )
            
            # Spatial join to map points to grid
            joined = gpd.sjoin(climate_gdf, grid_gdf, how='left', op='within')
            
            # Drop rows without a grid_id
            joined = joined.dropna(subset=['grid_id'])
            joined['grid_id'] = joined['grid_id'].astype(int)
            
            # Calculate centroids
            grid_centroids = grid_gdf.copy()
            grid_centroids['centroid'] = grid_centroids.geometry.centroid
            grid_centroids['centroid_lat'] = grid_centroids.centroid.y
            grid_centroids['centroid_long'] = grid_centroids.centroid.x
            grid_centroids = grid_centroids[['grid_id', 'centroid_lat', 'centroid_long']]
            
            # Aggregate data per grid_id
            aggregated = joined.groupby('grid_id').agg({
                'temperature': 'mean',
                'precipitation': 'sum',
                'dewpoint': 'mean',
                'wind_speed': 'mean',
                'soil_temp_top_layer': 'mean'
            }).reset_index()
            
            # Merge with centroids
            final_df = pd.merge(aggregated, grid_centroids, on='grid_id', how='left')
            
            # Reorder columns
            final_df = final_df[['grid_id', 'centroid_lat', 'centroid_long', 'temperature', 'precipitation', 'dewpoint', 'wind_speed', 'soil_temp_top_layer']]
            
            # Rename columns
            final_df.rename(columns={
                'centroid_lat': 'lat',
                'centroid_long': 'long',
                'soil_temp_top_layer': 'soil_top_layer'
            }, inplace=True)
            
            # Save to CSV
            final_df.to_csv(final_csv, index=False)
        
    except Exception as e:
        print(f"[climate_data_fetcher.py] ERROR: {e}")
