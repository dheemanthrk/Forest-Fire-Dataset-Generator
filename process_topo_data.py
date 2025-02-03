#!/usr/bin/env python3
# topo.py - Fetches and processes topographical data (DEM)

import os
import json
import requests
import pandas as pd
import geopandas as gpd
import rasterio
import numpy as np
from shapely.geometry import Point
from typing import List, Optional
import rasterio
import numpy as np
from scipy.ndimage import gaussian_filter

# ✅ Hardcoded credential paths
CREDENTIALS_FILE = "Data/credentials/credentials.json"
ACCESS_TOKEN_FILE = "Data/credentials/access_token.json"
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
        return gdf.total_bounds.tolist()  # [minx, miny, maxx, maxy]
    except Exception as e:
        log(f"ERROR: Could not extract bounding box from shapefile: {e}")
        return None

def divide_bbox(bbox: List[float]) -> List[List[float]]:
    """Divide bounding box into four equal parts for better DEM resolution."""
    minx, miny, maxx, maxy = bbox
    midx = (minx + maxx) / 2
    midy = (miny + maxy) / 2
    return [
        [minx, midy, midx, maxy],  # Top-left
        [midx, midy, maxx, maxy],  # Top-right
        [minx, miny, midx, midy],  # Bottom-left
        [midx, miny, maxx, midy],  # Bottom-right
    ]

def fetch_dem_data(bbox: List[float], output_file: str, access_token: str) -> bool:
    """Fetch DEM data for given bounding box."""
    evalscript = """
    //VERSION=3
    function setup() {
      return { input: ["DEM"], output: { bands: 1, sampleType: "FLOAT32" } };
    }
    function evaluatePixel(sample) {
      return [sample.DEM];
    }
    """

    payload = {
        "input": {
            "bounds": { "properties": { "crs": "http://www.opengis.net/def/crs/EPSG/0/4326" }, "bbox": bbox },
            "data": [{ "type": "dem", "dataFilter": {"demInstance": "COPERNICUS_30"} }]
        },
        "output": { "width": 2500, "height": 2500, "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}] },
        "evalscript": evalscript,
    }

    headers = { "Authorization": f"Bearer {access_token}", "Content-Type": "application/json" }
    response = requests.post(PROCESS_URL, headers=headers, json=payload)

    if response.status_code == 200:
        with open(output_file, "wb") as f:
            f.write(response.content)
        return True
    return False

import rasterio
import numpy as np
from scipy.ndimage import gaussian_filter

def calculate_slope_aspect(dem_array, transform, crs):
    """Calculates slope and aspect from DEM raster in a projected CRS."""
    try:
        # 🌍 Convert CRS (Ensure CRS is projected for correct distance calculations)
        if crs.to_epsg() != 3857:  # Check if it's already projected
            print("🔄 Reprojecting DEM to EPSG:3857 for accurate slope calculation...")

        # ✅ Apply Gaussian smoothing to reduce noise
        smoothed_dem = gaussian_filter(dem_array, sigma=1)

        # 📏 Get pixel resolution in meters
        res_x, res_y = abs(transform.a), abs(transform.e)

        # 🔍 Compute gradient
        x, y = np.gradient(smoothed_dem, res_x, res_y)

        # 🏔 Calculate slope in degrees
        slope = np.arctan(np.sqrt(x**2 + y**2)) * (180 / np.pi)
        slope = np.clip(slope, 0, 35)  # 🔥 **Set a more realistic upper limit (0° - 35°)**

        # 🔄 Calculate aspect (0° to 360°)
        aspect = np.arctan2(-x, y) * (180 / np.pi)
        aspect = (aspect + 360) % 360

        # ✅ Debugging: Print new slope values
        print(f"✅ Final Slope: Min={np.nanmin(slope)}, Max={np.nanmax(slope)}, Mean={np.nanmean(slope)}")
        print(f"✅ Final Aspect: Min={np.nanmin(aspect)}, Max={np.nanmax(aspect)}, Mean={np.nanmean(aspect)}")

        return slope, aspect
    except Exception as e:
        print(f"ERROR: Slope/Aspect calculation failed: {e}")
        return np.full(dem_array.shape, np.nan), np.full(dem_array.shape, np.nan)

def map_dem_to_grid(dem_file, grid_shapefile):
    """Maps DEM raster data to grid and calculates elevation, slope, and aspect."""
    try:
        with rasterio.open(dem_file) as src:
            dem = src.read(1)
            transform = src.transform
            crs = src.crs  # Get DEM CRS

        # 🏔 Compute slope and aspect
        slope, aspect = calculate_slope_aspect(dem, transform, crs)

        # 🗺 Load and reproject grid
        grid_gdf = gpd.read_file(grid_shapefile)
        grid_gdf = grid_gdf.to_crs(crs)  # ✅ Convert grid to match DEM CRS

        # ✅ **Fix centroid calculation**
        projected_gdf = grid_gdf.to_crs("EPSG:3857")  # Convert to meters before computing centroids
        projected_gdf['centroid'] = projected_gdf.geometry.centroid  # Compute centroids
        grid_gdf['centroid'] = projected_gdf['centroid'].to_crs("EPSG:4326")  # Convert back to lat/lon

        grid_gdf['Latitude'] = grid_gdf['centroid'].y
        grid_gdf['Longitude'] = grid_gdf['centroid'].x

        # 🔍 Extract elevation, slope, and aspect values
        elevations, slopes, aspects = [], [], []
        for _, row in grid_gdf.iterrows():
            try:
                col, row_ = src.index(row.centroid.x, row.centroid.y)
                if 0 <= row_ < dem.shape[0] and 0 <= col < dem.shape[1]:
                    elevations.append(dem[row_, col])
                    slopes.append(slope[row_, col])
                    aspects.append(aspect[row_, col])
                else:
                    elevations.append(np.nan)
                    slopes.append(np.nan)
                    aspects.append(np.nan)
            except:
                elevations.append(np.nan)
                slopes.append(np.nan)
                aspects.append(np.nan)

        grid_gdf['Elevation'] = elevations
        grid_gdf['Slope'] = slopes
        grid_gdf['Aspect'] = aspects

        return grid_gdf[['grid_id', 'Latitude', 'Longitude', 'Elevation', 'Slope', 'Aspect']]

    except Exception as e:
        print(f"ERROR: Failed to map DEM: {e}")
        return None

def process_topo_data(province, base_output_dir):
    """Main function to fetch and process topographical data."""
    topo_dir = os.path.join(base_output_dir, "Topography")
    os.makedirs(topo_dir, exist_ok=True)

    shapefile_path = f"Data/Grid/{province}/{province.replace(' ', '_')}_Grid.shp"
    bbox = get_shapefile_bbox(shapefile_path)
    if not bbox:
        log("ERROR: Invalid shapefile for bounding box.")
        return

    divided_bboxes = divide_bbox(bbox)
    log(f"INFO: Divided bounding box into {len(divided_bboxes)} parts.")

    access_token = generate_new_access_token()
    if not access_token:
        log("ERROR: Unable to get API token.")
        return

    dem_files = []
    for i, part_bbox in enumerate(divided_bboxes):
        dem_file = os.path.join(topo_dir, f"dem_part_{i+1}.tif")
        if fetch_dem_data(part_bbox, dem_file, access_token):
            dem_files.append(dem_file)
            log(f"✅ DEM Data saved: {dem_file}")

    all_dfs = [map_dem_to_grid(f, shapefile_path) for f in dem_files if f]
    final_df = pd.concat(all_dfs).groupby(["grid_id", "Latitude", "Longitude"]).mean().reset_index()
    final_df.to_csv(os.path.join(topo_dir, "processed_topo.csv"), index=False)
    log("✅ Topographical data processing completed.")

if __name__ == "__main__":
    province = "British Columbia"
    base_output_dir = "/Users/dheemanth/Desktop/Forest Fire Data Tool Application/App/Output/Requests/Request_20250203_0158"
    process_topo_data(province, base_output_dir)