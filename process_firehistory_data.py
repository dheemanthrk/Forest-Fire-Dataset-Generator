import os
import sys
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from datetime import datetime

def process_fire_history(province, start_date, end_date, base_output_dir):
    """
    Process fire history data by:
    1. Filtering fire records within the given date range.
    2. Mapping fire incidents to grid cells.
    3. Assigning grid centroids to each incident.
    
    Args:
        province (str): Name of the province.
        start_date (str): Start date in YYYY-MM-DD format.
        end_date (str): End date in YYYY-MM-DD format.
        base_output_dir (str): Base directory for storing output files.
    """
    
    # **1️⃣ Setup Paths**
    request_dir = os.path.join(base_output_dir, "FireHistory")
    os.makedirs(request_dir, exist_ok=True)

    fire_history_csv = "Data/FireHistory/fire_history.txt"  # Hardcoded fire history path
    shapefile_path = f"Data/Grid/{province}/{province.replace(' ', '_')}_Grid.shp"

    if not os.path.exists(fire_history_csv):
        raise FileNotFoundError(f"Fire history file not found: {fire_history_csv}")
    if not os.path.exists(shapefile_path):
        raise FileNotFoundError(f"Shapefile not found: {shapefile_path}")

    output_csv = os.path.join(request_dir, "fire_history_processed.csv")

    # **2️⃣ Load Fire History Data**
    print(f"Loading fire history data from {fire_history_csv}...")
    fire_data = pd.read_csv(fire_history_csv, low_memory=False)
    
    # Convert dates and ensure numeric fire size
    fire_data['REP_DATE'] = pd.to_datetime(fire_data['REP_DATE'], errors='coerce')
    fire_data['SIZE_HA'] = pd.to_numeric(fire_data['SIZE_HA'], errors='coerce').fillna(0)

    # **3️⃣ Filter Fire Data for Given Date Range**
    print(f"Filtering fire history between {start_date} and {end_date}...")
    fire_data_filtered = fire_data[
        (fire_data['REP_DATE'] >= start_date) & (fire_data['REP_DATE'] <= end_date)
    ].copy()

    if fire_data_filtered.empty:
        print(f"No fire history data found for {province} between {start_date} and {end_date}.")
        return

    # **4️⃣ Convert Fire Data to GeoDataFrame**
    fire_data_filtered['geometry'] = fire_data_filtered.apply(
        lambda row: Point(row['LONGITUDE'], row['LATITUDE']), axis=1
    )
    fire_gdf = gpd.GeoDataFrame(fire_data_filtered, geometry='geometry', crs="EPSG:4326")

    # **5️⃣ Load Grid Shapefile**
    print(f"Loading grid shapefile for {province} from {shapefile_path}...")
    grid_gdf = gpd.read_file(shapefile_path)
    
    # Ensure CRS matches
    if grid_gdf.crs is None or grid_gdf.crs.to_epsg() != 4326:
        grid_gdf = grid_gdf.to_crs("EPSG:4326")

    # **6️⃣ Filter Fire Incidents within Grid Bounding Box**
    print("Filtering fire incidents within grid shapefile's bounding box...")
    minx, miny, maxx, maxy = grid_gdf.total_bounds
    fire_gdf = fire_gdf.cx[minx:maxx, miny:maxy]

    if fire_gdf.empty:
        print(f"No fire incidents found within the grid of {province}.")
        return

    # **7️⃣ Spatial Join: Map Fire Incidents to Grid Cells**
    print("Mapping fire incidents to grid cells...")
    joined_gdf = gpd.sjoin(fire_gdf, grid_gdf, how="left", predicate="within")

    if 'grid_id' not in joined_gdf.columns:
        raise ValueError("Spatial join failed. No 'grid_id' found.")

    # **8️⃣ Compute Centroids of Each Grid Cell**
    projected_gdf = grid_gdf.to_crs("EPSG:3857")  # Reproject for accurate centroids
    projected_gdf['centroid'] = projected_gdf.geometry.centroid
    grid_gdf['centroid'] = projected_gdf['centroid'].to_crs("EPSG:4326")

    grid_gdf['Latitude'] = grid_gdf['centroid'].apply(lambda point: point.y)
    grid_gdf['Longitude'] = grid_gdf['centroid'].apply(lambda point: point.x)

    centroids = grid_gdf[['grid_id', 'Latitude', 'Longitude']]

    # **9️⃣ Merge Centroids with Fire History Data**
    print("Merging centroid data into fire history records...")
    final_gdf = joined_gdf.merge(centroids, on='grid_id', how='left')

    # **🔟 Save Final Processed Data**
    final_gdf = final_gdf[['grid_id', 'Latitude', 'Longitude', 'REP_DATE', 'CAUSE', 'SIZE_HA']]
    final_gdf = final_gdf.rename(columns={
        'REP_DATE': 'Date',
        'CAUSE': 'Fire_Cause',
        'SIZE_HA': 'Fire_Size_HA'
    })

    final_gdf.to_csv(output_csv, index=False)
    print(f"✅ Fire history data saved: {output_csv}")