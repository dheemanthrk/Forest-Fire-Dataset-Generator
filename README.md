Here's the README file in proper Markdown format. You can copy and paste it directly into your repository as `README.md`.

---

# 🔥 Forest Fire Data Processing Tool 🌍

A comprehensive tool for processing **climate**, **NDVI**, **fire history**, and **topographical** data for machine learning-based forest fire prediction.

---

## 📂 Project Structure

```
├── 📁 Data
│   ├── 📁 Grid                  # Shapefiles for each province
│   ├── 📁 FireHistory           # Fire history dataset
│   ├── 📁 credentials           # API credentials (🚨 Not included in the repository)
│
├── 📁 Output
│   ├── 📁 Requests              # Stores all processed data per request
│       ├── 📁 Request_YYYYMMDD_HHMM
│           ├── 📁 Climate       # Processed climate data
│           ├── 📁 FireHistory   # Processed fire history data
│           ├── 📁 NDVI          # NDVI data (raw + interpolated)
│           ├── 📁 Topography    # DEM, slope, and aspect data
│           ├── 🗂 merged_data.csv  # Final merged dataset
│
├── 📜 process_climate.py        # Fetches & processes climate data
├── 📜 process_ndvi.py           # Fetches & processes NDVI data
├── 📜 process_fire_history.py   # Processes fire history data
├── 📜 process_topo.py           # Fetches & processes topographical data
├── 📜 merge_data.py             # Merges all processed data
├── 📜 main.py                   # Main script for execution
├── 📜 README.md                 # You're reading it! 📖
```

## 🔑 Setting Up CDS API Credentials

The **CDS API** (Copernicus Data Service) is required to fetch climate and topographical data. Follow these steps to set up your credentials:

### 1️⃣ **Create a CDS Account**
1. Go to the **Copernicus Climate Data Store (CDS)**:  
   [https://cds.climate.copernicus.eu/user/register](https://cds.climate.copernicus.eu/user/register)
2. Register for an account and verify your email.
3. Once logged in, go to **My Account** → **API key**.

### 2️⃣ **Locate Your API Credentials**
Your CDS API key will look something like this:

```
url: https://cds.climate.copernicus.eu/api/v2
key: 12345678-abcd-1234-efgh-56789abcdefg
```

### 3️⃣ **Set Up `.cdsapirc` File**
You need to store your API credentials in a hidden file `.cdsapirc` in your **home directory**.

#### 📍 **On Linux/Mac:**
1. Open a terminal and run:
   ```sh
   nano ~/.cdsapirc
   ```
2. Paste the following content, replacing `your-key`:
   ```
   url: https://cds.climate.copernicus.eu/api/v2
   key: 12345678-abcd-1234-efgh-56789abcdefg
   verify: 0
   ```
3. Save and exit (`CTRL + X`, then `Y`, then `ENTER`).

#### 📍 **On Windows:**
1. Open **Notepad** and paste the API key in the same format as above.
2. Save it as `.cdsapirc` in `C:\Users\YourUsername\`.
3. Make sure the file type is **All Files (`*.*`)** and not `.txt`.

### 4️⃣ **Verify Installation**
After setting up the credentials, verify they are working by running:
```sh
python -c "import cdsapi; c = cdsapi.Client(); print('CDS API setup successful!')"
```

If there are no errors, your CDS API is correctly configured! ✅

## 🔧 Setup Instructions

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-repo/forest-fire-tool.git
   cd forest-fire-tool
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Create the API credentials folder manually:**
   The **`Data/credentials`** folder is excluded from version control. Create it manually and add the required JSON files:

   ```
   ├── 📁 Data
   │   ├── 📁 credentials
   │       ├── credentials.json      # Contains API username & password
   │       ├── access_token.json     # Stores generated access tokens
   ```

4. **Populate `credentials.json`** with the following format:
   ```json
   {
     "username": "your_username",
     "password": "your_password"
   }
   ```

---

## 🚀 Running the Tool

### 1️⃣ **Run the Main Script**

```bash
python main.py
```

It will prompt you for:

- **Province** (e.g., `"Alberta"`)
- **Start Date** (`YYYY-MM-DD`)
- **End Date** (`YYYY-MM-DD`)

This script will:
✅ Download & process **climate**, **NDVI**, **fire history**, and **topographical** data  
✅ Merge everything into **one structured CSV file**  
✅ Save results under `Output/Requests/Request_YYYYMMDD_HHMM/`

---

## 📊 Understanding the Data Outputs

Each request generates a **timestamped folder** inside `Output/Requests/`.  
Inside this folder, you'll find:

### 🔹 **Climate Data (`aggregated_climate_data.csv`)**

| GridID | Date       | Wind Speed U | Wind Speed V | Temperature | Surface Pressure | Precipitation | Latitude | Longitude |
| ------ | ---------- | ------------ | ------------ | ----------- | ---------------- | ------------- | -------- | --------- |
| 1      | 2023-05-01 | -0.37        | -0.27        | 276.23      | 80018.0          | 1.28e-06      | 53.34    | -119.68   |

---

### 🔹 **Fire History (`fire_history_processed.csv`)**

| grid_id | Date       | Total Fire Size | Fire Occurred | Fire Cause | Latitude | Longitude |
| ------- | ---------- | --------------- | ------------- | ---------- | -------- | --------- |
| 436     | 2023-05-01 | 6422.17         | 1             | Natural    | 56.30    | -119.98   |

🚨 **If no fire data is found for a grid,**

- `Fire_Occurred = 0`
- `Total_Fire_Size = 0`
- `Fire_Cause = NaN`

---

### 🔹 **NDVI Data (`interpolated_ndvi.csv`)**

| grid_id | date       | ndvi |
| ------- | ---------- | ---- |
| 1       | 2023-05-01 | 0.34 |
| 2       | 2023-05-01 | 0.29 |

🚨 **If no NDVI is found, NDVI = NaN**

---

### 🔹 **Topographical Data (`processed_topo.csv`)**

| grid_id | Latitude | Longitude | Elevation | Slope | Aspect |
| ------- | -------- | --------- | --------- | ----- | ------ |
| 1       | 53.34    | -119.68   | 962.05    | 35.0  | 161.71 |

🚨 **If no data found, values will be NaN**

---

### 🔹 **Final Merged Dataset (`merged_data.csv`)**

| grid_id | Latitude | Longitude | Date       | Climate Variables | Fire History | NDVI | Topography |
| ------- | -------- | --------- | ---------- | ----------------- | ------------ | ---- | ---------- |
| 1       | 53.34    | -119.68   | 2023-05-01 | ✅                | ✅           | ✅   | ✅         |
| 2       | 53.43    | -119.74   | 2023-05-01 | ✅                | ❌           | ✅   | ✅         |

🚨 **Missing values are handled as `NaN` for ML compatibility.**

---

## 🛠 Troubleshooting

### ❌ **Issue: "No API token found"**

✅ **Fix**: Run the following command to create & store an access token:

```bash
python generate_token.py
```

### ❌ **Issue: "Data missing in final CSV"**

- Ensure all individual scripts **ran successfully** inside `Output/Requests/Request_YYYYMMDD_HHMM/`
- If any data is missing, check logs and rerun that specific script.

---

## 🔮 Future Enhancements

✔ Add more **weather variables** like humidity & solar radiation  
✔ Support **larger regions** by dividing grids dynamically  
✔ Improve **data interpolation** for NDVI

---

## ❤️ Contributing

Feel free to submit **pull requests** or report **issues**!

---

🚀 **Developed by:** Dheemanth 
📅 **Last Updated:** `2025-02-03`

---

This README should provide everything needed for new users to **set up, run, and understand** the tool. Let me know if you'd like any refinements! 🚀🔥
