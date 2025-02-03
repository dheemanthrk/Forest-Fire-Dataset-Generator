import os
import pandas as pd
import numpy as np

def merge_final_dataset(request_id, start_date, end_date, base_output_dir="Output/Requests"):
    """
    Merges climate, fire history, NDVI, and topo datasets into a single CSV file.
    Filters the final dataset to include only rows within the given date range.

    Args:
        request_id (str): The request ID folder name (e.g., "Request_20250203_0158").
        start_date (str): Start date in YYYY-MM-DD format.
        end_date (str): End date in YYYY-MM-DD format.
        base_output_dir (str): Base directory for storing output files.

    Output:
        Saves a final merged CSV inside the request folder.
    """

    # ✅ Define paths for each dataset
    request_dir = os.path.join(base_output_dir, f"Request_{request_id}")
    
    climate_file = os.path.join(request_dir, "Climate", "aggregated_climate_data.csv")
    fire_file = os.path.join(request_dir, "FireHistory", "fire_history_processed.csv")
    ndvi_file = os.path.join(request_dir, "NDVI", "interpolated_ndvi.csv")
    topo_file = os.path.join(request_dir, "Topography", "processed_topo.csv")
    
    output_file = os.path.join(request_dir, "final_merged_dataset.csv")

    # ✅ Load datasets (Check if they exist)
    datasets = {}
    for name, path in {"climate": climate_file, "fire": fire_file, "ndvi": ndvi_file, "topo": topo_file}.items():
        if os.path.exists(path):
            datasets[name] = pd.read_csv(path)
            print(f"✅ Loaded {name} data: {path}")
        else:
            print(f"⚠️ WARNING: {name} data file not found: {path}")

    # ❌ If climate dataset is missing, stop merging
    if "climate" not in datasets:
        print("❌ ERROR: Climate dataset is missing. Merging cannot proceed.")
        return

    # ✅ Start with Climate Data as the base
    merged_df = datasets["climate"].copy()

    # 🔥 Fix GridID issue in Climate Data
    if "GridID" in merged_df.columns:
        merged_df = merged_df.rename(columns={"GridID": "grid_id"})

    # 🔥 Ensure 'Date' column exists in Climate Data
    if "Date" not in merged_df.columns:
        print("❌ ERROR: Climate data is missing the 'Date' column!")
        return

    # ✅ Convert 'Date' column to datetime for filtering
    merged_df["Date"] = pd.to_datetime(merged_df["Date"])

    # 🔥 Merge Fire History Data (on grid_id & Date)
    if "fire" in datasets:
        fire_df = datasets["fire"]
        
        # 🔄 Ensure Fire Data has 'Date' Column
        if "Date" not in fire_df.columns:
            print("⚠️ WARNING: Fire data missing 'Date' column. Renaming 'date' to 'Date'.")
            fire_df.rename(columns={"date": "Date"}, inplace=True)

        fire_df["Date"] = pd.to_datetime(fire_df["Date"])

        merged_df = merged_df.merge(
            fire_df, on=["grid_id", "Date"], how="left", suffixes=("", "_fire")
        )
        # ✅ Fill missing Fire History values
        merged_df["Total_Fire_Size"].fillna(0, inplace=True)  # No fire, size = 0
        merged_df["Fire_Occurred"].fillna(0, inplace=True)  # No fire = 0
        merged_df["Fire_Cause"].fillna("None", inplace=True)  # No fire cause = None

    else:
        # If fire data is missing, create placeholder columns
        merged_df["Total_Fire_Size"] = 0
        merged_df["Fire_Occurred"] = 0
        merged_df["Fire_Cause"] = "None"

    # 🌿 Merge NDVI Data (on grid_id & Date)
    if "ndvi" in datasets:
        ndvi_df = datasets["ndvi"]
        
        # 🔄 Ensure NDVI Data has 'Date' Column
        if "Date" not in ndvi_df.columns and "date" in ndvi_df.columns:
            print("⚠️ WARNING: NDVI data missing 'Date' column. Renaming 'date' to 'Date'.")
            ndvi_df.rename(columns={"date": "Date"}, inplace=True)

        ndvi_df["Date"] = pd.to_datetime(ndvi_df["Date"])

        merged_df = merged_df.merge(
            ndvi_df, on=["grid_id", "Date"], how="left", suffixes=("", "_ndvi")
        )
        merged_df["ndvi"].fillna(np.nan, inplace=True)  # Missing NDVI = NaN
    else:
        merged_df["ndvi"] = np.nan

    # 🏔 Merge Topo Data (Only on grid_id, NOT Date)
    if "topo" in datasets:
        merged_df = merged_df.merge(
            datasets["topo"], on="grid_id", how="left", suffixes=("", "_topo")
        )
        merged_df["Elevation"].fillna(np.nan, inplace=True)
        merged_df["Slope"].fillna(np.nan, inplace=True)
        merged_df["Aspect"].fillna(np.nan, inplace=True)
    else:
        merged_df["Elevation"] = np.nan
        merged_df["Slope"] = np.nan
        merged_df["Aspect"] = np.nan

    # ✅ Filter dataset to only include rows within the given date range
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    merged_df = merged_df[(merged_df["Date"] >= start_date) & (merged_df["Date"] <= end_date)]

    # ✅ Final Column Reordering
    column_order = [
        "grid_id", "Latitude", "Longitude", "Date",
        "Wind_Speed_U_10m", "Wind_Speed_V_10m", "Dew_Point_2m_C", "Temperature_2m_C", "Surface_Pressure_Pa", "Total_Precip_mm",
        "Total_Fire_Size", "Fire_Occurred", "Fire_Cause",
        "ndvi",
        "Elevation", "Slope", "Aspect"
    ]

    # 🛠️ Ensure only existing columns are included
    merged_df = merged_df[[col for col in column_order if col in merged_df.columns]]

    # ✅ Save Final Dataset
    merged_df.to_csv(output_file, index=False)
    print(f"✅ Final merged dataset saved: {output_file}")
