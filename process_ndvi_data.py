import os
import json
import requests
import pandas as pd
import geopandas as gpd
import rasterio
import numpy as np
from datetime import datetime, timedelta
from shapely.geometry import Point

# ✅ Hardcoded credential paths
CREDENTIALS_FILE = "Data/Credentials/credentials.json"
ACCESS_TOKEN_FILE = "Data/Credentials/access_token.json"
TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

def log(message: str):
    """Logging function."""
    print(message)

def load_access_token():
    """Load the saved access token."""
    try:
        with open(ACCESS_TOKEN_FILE, "r") as f:
            return json.load(f).get("access_token")
    except Exception as e:
        log(f"ERROR: Could not load access token: {e}")
        return None

def generate_new_access_token():
    """Generate and save a new access token."""
    try:
        with open(CREDENTIALS_FILE, "r") as f:
            creds = json.load(f)
            username, password = creds.get("username"), creds.get("password")

        if not username or not password:
            log("ERROR: Missing username or password in credentials.")
            return None

        payload = {
            "client_id": "cdse-public",
            "username": username,
            "password": password,
            "grant_type": "password"
        }

        log("INFO: Requesting new access token...")
        response = requests.post(TOKEN_URL, data=payload)

        if response.status_code == 200:
            access_token = response.json().get("access_token")
            with open(ACCESS_TOKEN_FILE, "w") as f:
                json.dump({"access_token": access_token}, f)
            log("INFO: New access token saved.")
            return access_token
        else:
            log(f"ERROR: Failed to obtain token: {response.text}")

    except Exception as e:
        log(f"ERROR: Exception during token generation: {e}")

    return None

def get_shapefile_bbox(shapefile):
    """Extract bounding box from shapefile."""
    try:
        gdf = gpd.read_file(shapefile)
        if gdf.crs is None or gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")
        bbox = gdf.total_bounds.tolist()  # [minx, miny, maxx, maxy]
        return bbox
    except Exception as e:
        log(f"ERROR: Could not extract bounding box from shapefile: {e}")
        return None

def fetch_ndvi_data(min_lon, min_lat, max_lon, max_lat, date_str, output_file, headers):
    """Fetch NDVI data for a given date and bounding box."""
    evalscript = """
    //VERSION=3
    function setup() {
      return { input: ["B04", "B08"], output: { bands: 1, sampleType: "FLOAT32" } };
    }
    function evaluatePixel(sample) {
      let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
      return [ndvi];
    }
    """
    payload = {
        "input": {
            "bounds": { "properties": { "crs": "http://www.opengis.net/def/crs/EPSG/0/4326" }, "bbox": [min_lon, min_lat, max_lon, max_lat] },
            "data": [{ "type": "sentinel-2-l2a", "dataFilter": { "timeRange": { "from": f"{date_str}T00:00:00Z", "to": f"{date_str}T23:59:59Z" } } }]
        },
        "output": { "width": 2500, "height": 2500, "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}] },
        "evalscript": evalscript,
    }

    response = requests.post(PROCESS_URL, headers=headers, json=payload)
    if response.status_code == 200:
        with open(output_file, "wb") as f:
            f.write(response.content)
        return True
    return False

def map_ndvi_to_grid(ndvi_tif, grid_shapefile):
    """Map NDVI raster data to a grid shapefile."""
    try:
        with rasterio.open(ndvi_tif) as src:
            ndvi_array = src.read(1)
            grid_gdf = gpd.read_file(grid_shapefile).to_crs(src.crs)
            ndvi_values = []

            for _, row in grid_gdf.iterrows():
                centroid = row.geometry.centroid
                col, row_ = src.index(centroid.x, centroid.y)
                ndvi_values.append(ndvi_array[row_, col])

            grid_gdf['ndvi'] = ndvi_values
            return grid_gdf[['grid_id', 'ndvi']]
    except Exception as e:
        log(f"ERROR: Failed to map NDVI: {e}")
        return None

def interpolate_ndvi(ndvi_df):
    """Interpolate NDVI to daily values."""
    ndvi_pivot = ndvi_df.pivot(index='grid_id', columns='date', values='ndvi').interpolate(axis=1, method='linear')
    return ndvi_pivot.reset_index().melt(id_vars='grid_id', var_name='date', value_name='ndvi')

def process_ndvi_data(province, start_date, end_date, base_output_dir):
    """Main function to fetch and process NDVI data."""
    ndvi_dir = os.path.join(base_output_dir, "NDVI")
    os.makedirs(ndvi_dir, exist_ok=True)

    shapefile_path = f"Data/Grid/{province}/{province.replace(' ', '_')}_Grid.shp"
    bbox = get_shapefile_bbox(shapefile_path)
    if not bbox:
        log("ERROR: Invalid shapefile for bounding box.")
        return

    access_token = generate_new_access_token()
    if not access_token:
        log("ERROR: Unable to get API token.")
        return

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    min_lon, min_lat, max_lon, max_lat = bbox
    ndvi_records = []

    date_range = pd.date_range(start=start_date, end=end_date, freq="5D")
    for date_str in date_range.strftime("%Y-%m-%d"):
        output_tif = os.path.join(ndvi_dir, f"ndvi_{date_str}.tif")
        if fetch_ndvi_data(min_lon, min_lat, max_lon, max_lat, date_str, output_tif, headers):
            ndvi_df = map_ndvi_to_grid(output_tif, shapefile_path)
            if ndvi_df is not None:
                ndvi_df['date'] = date_str
                ndvi_records.append(ndvi_df)

    if ndvi_records:
        processed_ndvi = pd.concat(ndvi_records, ignore_index=True)
        processed_ndvi.to_csv(os.path.join(ndvi_dir, "processed_ndvi.csv"), index=False)

        interpolated_ndvi = interpolate_ndvi(processed_ndvi)
        interpolated_ndvi.to_csv(os.path.join(ndvi_dir, "interpolated_ndvi.csv"), index=False)
        log("INFO: NDVI processing completed.")

def main():
    print("🚀 Starting NDVI Processing...")
    
    province = "Alberta"
    start_date = "2023-01-01"
    end_date = "2023-01-05"
    base_output_dir = "/Users/dheemanth/Desktop/Forest Fire Data Tool Application/App/Output/Requests/Request_20250203_0158"

    # Check if the directory exists
    if not os.path.exists(base_output_dir):
        print(f"⚠️ Base output directory '{base_output_dir}' does not exist. Creating it...")
        os.makedirs(base_output_dir, exist_ok=True)

    print(f"✅ Output will be saved in: {base_output_dir}")

    # Run NDVI Processing
    process_ndvi_data(province, start_date, end_date, base_output_dir)

    print("✅ NDVI Processing Completed.")

if __name__ == "__main__":
    main()
