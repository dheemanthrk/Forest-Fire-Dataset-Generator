import pandas as pd
import numpy as np

# Load dataset
data = pd.read_csv("/Users/dheemanth/Desktop/Forest Fire Dataset Generation tool/App/final.csv")

# Fill missing values in fire_occurred with 0.0
data['fire_occurred'] = data['fire_occurred'].fillna(0.0)

# Fill missing values in meteorological and geographical features with 0.0
features_to_fill = [
    'mean_dew_point_temperature', 'mean_soil_water_top_layer',
    'mean_solar_radiation', 'mean_temperature_2m',
    'mean_total_precipitation', 'mean_wind_speed_u', 'mean_wind_speed_v',
    'elevation', 'slope', 'aspect', 'ndvi'
]
data[features_to_fill] = data[features_to_fill].fillna(0.0)

# Fill missing fire_size with 0.0
data['fire_size'] = data['fire_size'].fillna(0.0)

# Drop the problematic fire_cause column
if 'fire_cause' in data.columns:
    data = data.drop('fire_cause', axis=1)

# Ensure fire_occurred is an integer
data['fire_occurred'] = data['fire_occurred'].astype(int)

# Save the preprocessed dataset
data.to_csv("preprocessed_dataset_no_fire_cause.csv", index=False)
