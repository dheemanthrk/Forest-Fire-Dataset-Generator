import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QScrollArea, QComboBox, QRadioButton, QHBoxLayout, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import plotly.express as px
from PyQt5.QtCore import QTimer
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import NearMiss
from imblearn.combine import SMOTEENN
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np
import subprocess
from process_climate_data import process_climate_data
from datetime import datetime
import os
from process_firehistory_data import process_fire_history
from process_ndvi_data import process_ndvi_data
from process_topo_data import process_topo_data
from merge_final_dataset import merge_final_dataset

class ForestFireApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Forest Fire Dataset Generation Tool")
        self.setGeometry(100, 100, 800, 600)

        self.initUI()

    def initUI(self):
        # Create a tab widget
        self.tabs = QTabWidget()

        # Add tabs
        self.tabs.addTab(self.create_setup_tab(), "Setup")
        self.tabs.addTab(self.create_info_tab(), "Info")
        self.tabs.addTab(self.create_credentials_tab(), "Credentials")
        self.tabs.addTab(self.create_visualize_tab(), "Visualize")

        # Terminal output box
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setStyleSheet("background-color: black; color: white; font-family: monospace;")
        self.terminal_output.setMinimumHeight(150)

        # Clear Terminal Button
        self.clear_terminal_button = QPushButton("Clear Terminal")
        self.clear_terminal_button.clicked.connect(self.clear_terminal)

        # Main layout
        terminal_layout = QVBoxLayout()
        terminal_layout.addWidget(self.clear_terminal_button)
        terminal_layout.addWidget(QLabel("Terminal Output:"))
        terminal_layout.addWidget(self.terminal_output)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        main_layout.addLayout(terminal_layout)

        # Set central widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def create_setup_tab(self):
        """Create the Setup tab."""
        setup_tab = QWidget()
        layout = QGridLayout()

        # ----- Top-Left: Province and Date Inputs -----
        province_label = QLabel("Province:")
        self.province_dropdown = QComboBox()
        self.province_dropdown.addItems([
            "Alberta", "British Columbia", "Manitoba", "New Brunswick",
            "Newfoundland and Labrador", "Northwest Territories", "Nova Scotia",
            "Nunavut", "Ontario", "Prince Edward Island", "Quebec", "Saskatchewan", "Yukon"
        ])

        start_date_label = QLabel("Start Date")
        self.start_date_input = QLineEdit()
        end_date_label = QLabel("End Date")
        self.end_date_input = QLineEdit()

        top_left_layout = QVBoxLayout()
        top_left_layout.addWidget(province_label)
        top_left_layout.addWidget(self.province_dropdown)
        top_left_layout.addWidget(start_date_label)
        top_left_layout.addWidget(self.start_date_input)
        top_left_layout.addWidget(end_date_label)
        top_left_layout.addWidget(self.end_date_input)

        # ----- Top-Right: CSV Input, Balancing Dropdown, Sampling Ratio, and Buttons -----

        # Browse CSV Section
        browse_csv_label = QLabel("Browse CSV Input")
        self.csv_input = QLineEdit()

        browse_button = QPushButton("Browse CSV")
        browse_button.clicked.connect(lambda: self.browse_csv_setup('class'))

        # Check Class Distribution Button
        self.check_distribution_button = QPushButton("Check Class Distribution")
        self.check_distribution_button.clicked.connect(self.check_class_distribution)

        # Layout for CSV Input and Buttons
        csv_layout = QHBoxLayout()
        csv_layout.addWidget(self.csv_input)
        csv_layout.addWidget(browse_button)
        csv_layout.addWidget(self.check_distribution_button)

        # Balance Data Section
        balance_label = QLabel("Balance Data:")
        self.balance_dropdown = QComboBox()
        self.balance_dropdown.addItems(["SMOTE", "NearMiss-3", "SMOTE+ENN"])

        # Sampling Ratio Dropdown
        sampling_label = QLabel("Sampling Ratio:")
        self.sampling_ratio_dropdown = QComboBox()
        self.sampling_ratio_dropdown.addItems([f"{i}%" for i in range(0, 101, 10)])

        balance_button = QPushButton("Balance Data")
        balance_button.clicked.connect(self.balance_data)

        # Layout for Balance Data, Sampling Ratio, and Button
        balance_sampling_layout = QHBoxLayout()
        balance_sampling_layout.addWidget(self.balance_dropdown)
        balance_sampling_layout.addWidget(sampling_label)
        balance_sampling_layout.addWidget(self.sampling_ratio_dropdown)
        balance_sampling_layout.addWidget(balance_button)

        # Final Layout for Top-Right Section
        top_right_layout = QVBoxLayout()
        top_right_layout.addWidget(browse_csv_label)
        top_right_layout.addLayout(csv_layout)
        top_right_layout.addWidget(balance_label)
        top_right_layout.addLayout(balance_sampling_layout)


        # ----- Bottom-Left: Run Button -----
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_tool)
        bottom_left_layout = QVBoxLayout()
        bottom_left_layout.addStretch()
        bottom_left_layout.addWidget(self.run_button, alignment=Qt.AlignCenter)
        bottom_left_layout.addStretch()

        # ----- Bottom-Right: Model Selection and Train Button -----
        model_label = QLabel("Train Model:")
        self.model_dropdown = QComboBox()
        self.model_dropdown.addItems(["Linear Regression", "Random Forest", "XGBoost", "LightGBM"])

        train_button = QPushButton("Train Model")
        train_button.clicked.connect(self.train_model)

        bottom_right_layout = QVBoxLayout()
        bottom_right_layout.addWidget(model_label)
        bottom_right_layout.addWidget(self.model_dropdown)
        bottom_right_layout.addWidget(train_button, alignment=Qt.AlignCenter)

        # ----- Add Layouts to Grid -----
        layout.addLayout(top_left_layout, 0, 0)    # Top-Left
        layout.addLayout(top_right_layout, 0, 1)   # Top-Right
        layout.addLayout(bottom_left_layout, 1, 0) # Bottom-Left
        layout.addLayout(bottom_right_layout, 1, 1) # Bottom-Right

        # Set uniform spacing
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(20)
        layout.setContentsMargins(10, 10, 10, 10)

        setup_tab.setLayout(layout)
        return setup_tab

    def browse_csv_setup(self, file_type):
        """Open file dialog to browse for a CSV file."""
        file_name, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV Files (*.csv)")

        if file_name:
            # Update the input text field with the selected file path
            self.csv_input.setText(file_name)
            self.terminal_output.append(f"Selected {file_type} CSV file: {file_name}")
        else:
            self.terminal_output.append("No file selected.")

    def create_info_tab(self):
        """Create the Info tab."""
        info_tab = QWidget()
        layout = QVBoxLayout()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout()

        # Adding detailed info to the content
        content_layout.addWidget(QLabel("<b>Project Overview:</b>"))
        content_layout.addWidget(QLabel("This tool is designed for geospatial dataset generation, balancing, and machine learning evaluation, specifically focused on forest fire prediction. The system automates the process from data collection to model validation, ensuring efficient handling of large datasets with spatial and temporal features."))

        content_layout.addWidget(QLabel("<b>Key Features:</b>"))
        content_layout.addWidget(QLabel("1. Data Collection: Fetches climate, NDVI, topographical, and fire history data from multiple sources such as Copernicus, ERA5, and CWFIS."))
        content_layout.addWidget(QLabel("2. Data Balancing: Includes techniques like SMOTE, NearMiss, and SMOTE+ENN to handle data imbalance for improved model training."))
        content_layout.addWidget(QLabel("3. Machine Learning Models: Supports models like Logistic Regression, Random Forest, XGBoost, and LightGBM for forest fire prediction."))
        content_layout.addWidget(QLabel("4. Visualization: Provides tools for visualizing the dataset and the model's performance metrics (accuracy, precision, recall, F1-score)."))
        content_layout.addWidget(QLabel("5. User Customization: Allows users to define time ranges, spatial regions, and model parameters for customized data generation and analysis."))

        content_layout.addWidget(QLabel("<b>Inputs:</b>"))
        content_layout.addWidget(QLabel("• Temporal Range: Define the start and end dates for data collection."))
        content_layout.addWidget(QLabel("• Spatial Inputs: Select provinces or bounding boxes for specific geographic regions."))
        content_layout.addWidget(QLabel("• Resampling Techniques: Choose balancing techniques and specify sampling ratios."))

        content_layout.addWidget(QLabel("<b>Outputs:</b>"))
        content_layout.addWidget(QLabel("• Final Dataset: Cleaned, balanced dataset ready for training models."))
        content_layout.addWidget(QLabel("• Performance Metrics: Accuracy, precision, recall, F1 score, and ROC-AUC for evaluating model effectiveness."))

        content_layout.addWidget(QLabel("<b>Additional Info:</b>"))
        content_layout.addWidget(QLabel("• Platform: Built with Python using PyQt5 for the UI and integrated with various APIs for data fetching."))
        content_layout.addWidget(QLabel("• Data Sources: Combines multiple datasets from sources like Copernicus, ERA5, CWFIS, and more."))
        content_layout.addWidget(QLabel("• Scalability: Can handle large datasets and multiple regions, with support for different spatial and temporal resolutions."))

        content_layout.addWidget(QLabel("<b>Instructions:</b>"))
        content_layout.addWidget(QLabel("1. Set up your parameters by specifying the temporal range and spatial inputs."))
        content_layout.addWidget(QLabel("2. Choose your preferred data balancing method and machine learning model."))
        content_layout.addWidget(QLabel("3. Click 'Run' to start the automated process, which fetches, balances, and trains a model."))
        content_layout.addWidget(QLabel("4. Visualize results and download the dataset."))

        content.setLayout(content_layout)
        scroll_area.setWidget(content)

        layout.addWidget(scroll_area)
        info_tab.setLayout(layout)
        return info_tab

    def create_credentials_tab(self):
        """Create the Credentials tab."""
        credentials_tab = QWidget()
        layout = QGridLayout()

        layout.addWidget(QLabel("API Username:"), 0, 0)
        self.username_input = QLineEdit()
        layout.addWidget(self.username_input, 0, 1)

        layout.addWidget(QLabel("API Password:"), 1, 0)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input, 1, 1)

        save_button = QPushButton("Save Credentials")
        save_button.clicked.connect(self.save_credentials)
        layout.addWidget(save_button, 2, 0, 1, 2)

        credentials_tab.setLayout(layout)
        return credentials_tab

    def create_visualize_tab(self):
        """Create the Visualize tab."""
        visualize_tab = QWidget()
        layout = QVBoxLayout()

        # Province Selection
        layout.addWidget(QLabel("Select Province for Shapefile:"))
        self.province_dropdown_visualize = QComboBox()
        self.province_dropdown_visualize.addItems([
            "Alberta", "British Columbia", "Manitoba", "New Brunswick",
            "Newfoundland and Labrador", "Northwest Territories", "Nova Scotia",
            "Nunavut", "Ontario", "Prince Edward Island", "Quebec", "Saskatchewan", "Yukon"
        ])
        layout.addWidget(self.province_dropdown_visualize)

        # Grid Option
        self.grid_option_plain = QRadioButton("Plain (Without Grid)")
        self.grid_option_with_grid = QRadioButton("With Grid")
        self.grid_option_with_grid.setChecked(True)
        grid_layout = QHBoxLayout()
        grid_layout.addWidget(self.grid_option_plain)
        grid_layout.addWidget(self.grid_option_with_grid)
        layout.addLayout(grid_layout)

        # CSV Upload
        layout.addWidget(QLabel("Upload CSV:"))
        self.csv_input = QLineEdit()
        self.csv_browse_button = QPushButton("Browse")
        self.csv_browse_button.clicked.connect(self.browse_csv)
        csv_layout = QHBoxLayout()
        csv_layout.addWidget(self.csv_input)
        csv_layout.addWidget(self.csv_browse_button)
        layout.addLayout(csv_layout)

        # Column Dropdown
        layout.addWidget(QLabel("Select Column to Visualize:"))
        self.column_dropdown = QComboBox()
        layout.addWidget(self.column_dropdown)

        # Visualization Mode
        layout.addWidget(QLabel("Choose Visualization Mode:"))
        self.visualization_mode = QComboBox()
        self.visualization_mode.addItems(["Basic (Matplotlib)", "Advanced (Plotly)"])
        layout.addWidget(self.visualization_mode)

        # Visualization Button
        self.visualize_button = QPushButton("Visualize")
        self.visualize_button.clicked.connect(self.visualize_data)
        layout.addWidget(self.visualize_button)

        # Reset Button
        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_visualize_tab)
        layout.addWidget(self.reset_button)

        visualize_tab.setLayout(layout)
        return visualize_tab
    
    def reset_visualize_tab(self):
        """Reset all fields in the Visualize tab."""
        self.csv_input.clear()
        self.column_dropdown.clear()
        self.visualization_mode.setCurrentIndex(0)
        self.terminal_output.append("Visualize tab reset to initial state.")

    def browse_csv(self):
        """Browse and load a CSV file and populate column dropdown."""
        file_name, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV Files (*.csv)")
        if file_name:
            self.csv_input.setText(file_name)
            self.terminal_output.append(f"Selected CSV file: {file_name}")
            try:
                df = pd.read_csv(file_name)
                excluded_columns = {'grid_id', 'date', 'latitude', 'longitude'}
                available_columns = [col for col in df.columns if col not in excluded_columns]
                self.column_dropdown.clear()
                if available_columns:
                    self.column_dropdown.addItems(available_columns)
                    self.terminal_output.append(f"Available columns: {', '.join(available_columns)}")
                else:
                    self.terminal_output.append("No valid columns available for visualization.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load CSV: {str(e)}")
                self.terminal_output.append(f"Error reading CSV: {str(e)}")

    def visualize_data(self):
        """Visualize data based on user selections."""
        province = self.province_dropdown_visualize.currentText()
        visualization_mode = self.visualization_mode.currentText()
        grid_option = "Grid" if self.grid_option_with_grid.isChecked() else "Plain"
        file_path = self.csv_input.text()

        # Determine the shapefile path
        base_path = os.path.join(os.path.dirname(__file__), "Data")
        subfolder = "Grid" if grid_option == "Grid" else "Shapefile"
        shapefile_path = os.path.join(base_path, subfolder, province, f"{province}_{grid_option}.shp")

        # Validate shapefile existence
        if not os.path.exists(shapefile_path):
            QMessageBox.warning(self, "Input Error", f"Shapefile not found for {province} ({grid_option}).")
            self.terminal_output.append(f"Error: Shapefile not found for {province} ({grid_option}).")
            return

        # Check if CSV is uploaded
        if not file_path:
            QMessageBox.warning(self, "Input Error", "Please upload a CSV file.")
            return

        # Selected column
        selected_column = self.column_dropdown.currentText()
        if not selected_column:
            QMessageBox.warning(self, "Input Error", "Please select a column to visualize.")
            return

        # Call appropriate visualization function
        if visualization_mode == "Basic (Matplotlib)":
            self.basic_visualization(shapefile_path, file_path, selected_column, province)
        elif visualization_mode == "Advanced (Plotly)":
            self.advanced_visualization(shapefile_path, file_path, selected_column, province)

    def basic_visualization(self, shapefile_path, csv_path, column, province):
        """Basic visualization using Matplotlib."""
        import matplotlib.pyplot as plt
        import geopandas as gpd
        import pandas as pd
        from matplotlib.colors import Normalize
        from matplotlib.colorbar import ColorbarBase

        try:
            # Load data
            shapefile = gpd.read_file(shapefile_path)
            data = pd.read_csv(csv_path)

            # Merge shapefile and CSV data
            merged = shapefile.merge(data, on='grid_id')

            # Plot using Matplotlib
            fig, ax = plt.subplots(figsize=(12, 10))
            colormap = "terrain" if column == "elevation" else "viridis"

            merged.plot(
                ax=ax,
                column=column,
                cmap=colormap,
                legend=True,
                legend_kwds={'label': f"{column.capitalize()}", 'orientation': "vertical"}
            )
            ax.set_title(f"{province} - {column.capitalize()} Visualization", fontsize=14)
            ax.axis("off")
            plt.tight_layout()
            plt.show()

            self.terminal_output.append(f"Basic visualization of '{column}' completed.")

        except Exception as e:
            self.terminal_output.append(f"Error during basic visualization: {str(e)}")

    def advanced_visualization(self, shapefile_path, csv_path, column, province):
        """Advanced visualization using Plotly."""
        import geopandas as gpd
        import pandas as pd
        import plotly.express as px

        try:
            # Load data
            shapefile = gpd.read_file(shapefile_path)
            data = pd.read_csv(csv_path)

            # Merge shapefile and CSV data
            merged = shapefile.merge(data, on='grid_id')

            # Plot using Plotly
            fig = px.choropleth(
                merged,
                geojson=merged.geometry,
                locations=merged.index,
                color=column,
                hover_name="grid_id",
                color_continuous_scale="terrain" if column == "elevation" else "viridis",
                title=f"{province} - {column.capitalize()} Heatmap"
            )
            fig.update_geos(fitbounds="locations", visible=False)
            fig.show()

            self.terminal_output.append(f"Advanced visualization of '{column}' completed.")

        except Exception as e:
            self.terminal_output.append(f"Error during advanced visualization: {str(e)}")

    def visualize_shapefile_with_matplotlib(self, shapefile_path):
        """Visualize shapefile only using Matplotlib."""
        import geopandas as gpd
        import matplotlib.pyplot as plt

        try:
            shapefile_gdf = gpd.read_file(shapefile_path)

            # Plot shapefile
            fig, ax = plt.subplots(figsize=(10, 8))
            shapefile_gdf.plot(ax=ax, color="lightgrey", edgecolor="black")
            ax.set_title("Shapefile Visualization", fontsize=14)
            plt.show()

            self.terminal_output.append("Shapefile visualization completed using Matplotlib.")
        except Exception as e:
            self.terminal_output.append(f"Error visualizing shapefile with Matplotlib: {str(e)}")

    def visualize_shapefile_with_plotly(self, shapefile_path):
        """Visualize shapefile only using Plotly."""
        import geopandas as gpd
        import plotly.express as px

        try:
            shapefile_gdf = gpd.read_file(shapefile_path)

            # Plot shapefile
            fig = px.choropleth(
                shapefile_gdf,
                geojson=shapefile_gdf.geometry,
                locations=shapefile_gdf.index,
                title="Shapefile Visualization",
            )
            fig.update_geos(fitbounds="locations")
            fig.show()

            self.terminal_output.append("Shapefile visualization completed using Plotly.")
        except Exception as e:
            self.terminal_output.append(f"Error visualizing shapefile with Plotly: {str(e)}")

    def clear_terminal(self):
        """Clear the terminal output."""
        self.terminal_output.clear()

    def save_credentials(self):
        """Save credentials."""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        if not username or not password:
            self.terminal_output.append("Error: Username and password cannot be empty.")
            return
        self.terminal_output.append("Credentials saved successfully.")

    def check_class_distribution(self):
        """Check class distribution from the selected CSV."""
        file_name = self.class_csv_input.text()
        if not file_name:
            QMessageBox.warning(self, "Input Error", "Please select a CSV file for class distribution.")
            return

        try:
            df = pd.read_csv(file_name)
            class_distribution = df['fire_occurred'].value_counts()
            self.terminal_output.append("Class Distribution:")
            self.terminal_output.append(str(class_distribution))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to analyze class distribution: {str(e)}")
       
    def train_model(self):
        """Train ML model using selected CSV and model."""
        file_name = self.ml_csv_input.text()
        model_type = self.model_dropdown.currentText()

        if not file_name:
            QMessageBox.warning(self, "Input Error", "Please select a CSV file for ML training.")
            return

        try:
            df = pd.read_csv(file_name)
            X = df.drop('fire_occurred', axis=1)
            y = df['fire_occurred']

            if model_type == "Logistic Regression":
                from sklearn.linear_model import LogisticRegression
                model = LogisticRegression()
            elif model_type == "Random Forest":
                from sklearn.ensemble import RandomForestClassifier
                model = RandomForestClassifier()
            elif model_type == "SVM":
                from sklearn.svm import SVC
                model = SVC()
            elif model_type == "KNN":
                from sklearn.neighbors import KNeighborsClassifier
                model = KNeighborsClassifier()

            model.fit(X, y)
            self.terminal_output.append(f"Model {model_type} trained successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to train model: {str(e)}")

    # def run_tool(self):
    #     """Handle Run button click to simulate dataset generation with delays."""
    #     province = self.province_dropdown.currentText()
    #     start_date = self.start_date_input.text()
    #     end_date = self.end_date_input.text()

    #     if not province or not start_date or not end_date:
    #         QMessageBox.warning(self, "Input Error", "Please provide Province, Start Date, and End Date.")
    #         return

    #     self.terminal_output.append("===================================")
    #     self.terminal_output.append("RUNNING DATASET GENERATION PROCESS")
    #     self.terminal_output.append("===================================")
    #     self.terminal_output.append(f"Creating dataset for inputs: Province: {province}, Start Date: {start_date}, End Date: {end_date}")

    #     # Steps with delays
    #     steps = [
    #         (10, "--- Step 1: Extracting shapefile ---\nCreating grids...\nExtracting centroids..."),
    #         (30, "--- Step 2: Fetching meteorological data ---\nInitializing CDS API...\nWaiting for response...\nSkipping download for this input because file already exists.\nConverting NC to CSV...\nMapping meteorological data to grids..."),
    #         (30, "--- Step 3: Fetching NDVI data ---\nGenerating access token...\nFetching TIFF file...\nPerforming interpolation...\nMapping NDVI data to grids..."),
    #         (30, "--- Step 4: Fetching Elevation data ---\nGenerating access token...\nFetching DEM TIFF file...\nExtracting elevation, slope, and aspect...\nAssigning elevation data to grids..."),
    #         (10, "--- Step 5: Fetching Fire History ---\nFetching fire history data from TXT file...\nAssigning fire history data to grid IDs..."),
    #         (10, "--- Step 6: Spatial Integration and Preprocessing ---\nIntegrating all datasets...\nHandling missing values...\nPreprocessing complete.")
    #     ]

    #     # Initialize step execution
    #     self.execute_steps_with_delay(steps, province, start_date)


    def run_tool(self):
        """Run both climate and fire history processing functions with user inputs."""
        province = self.province_dropdown.currentText().strip()
        start_date = self.start_date_input.text().strip()
        end_date = self.end_date_input.text().strip()

        if not province or not start_date or not end_date:
            QMessageBox.warning(self, "Input Error", "Please provide Province, Start Date, and End Date.")
            return

        # ✅ Generate Request ID only ONCE
        request_id = datetime.now().strftime("%Y%m%d_%H%M")
        base_output_dir = os.path.join("Output/Requests", f"Request_{request_id}")
        os.makedirs(base_output_dir, exist_ok=True)  # Ensure request folder exists

        self.terminal_output.append(f"📌 Request ID: {request_id}")
        self.terminal_output.append(f"Processing data for {province} from {start_date} to {end_date}...")

        try:
            # ✅ Pass `base_output_dir` to climate & fire functions
            process_climate_data(province, start_date, end_date, base_output_dir)
            self.terminal_output.append("✅ Climate data processing completed.")

            process_fire_history(province, start_date, end_date, base_output_dir)
            self.terminal_output.append("✅ Fire history processing completed.")

            process_ndvi_data(province, start_date, end_date, base_output_dir)
            self.terminal_output.append("✅ NDVI data processing completed.")

            process_topo_data(province, base_output_dir)
            self.terminal_output.append("✅ Topographical data processing completed.")

            # ✅ Merge all datasets
            merge_final_dataset(request_id, start_date, end_date)
            self.terminal_output.append(f"✅ Data processing & merging completed. Final dataset saved in: {base_output_dir}")

        except Exception as e:
            self.terminal_output.append(f"❌ Error: {str(e)}")

    def execute_steps_with_delay(self, steps, province, start_date):
        """Execute each step with a delay."""
        def process_step(index):
            if index < len(steps):
                delay, message = steps[index]
                self.terminal_output.append(message)
                QTimer.singleShot(delay * 1000, lambda: process_step(index + 1))  # Delay in milliseconds
            else:
                # Final Output Path
                output_path = f"/Users/dheemanth/Desktop/Forest Fire Dataset Generation tool/App/Data/Output/{province}_{start_date[:7]}.csv"
                self.terminal_output.append(f"\nGenerated CSV is ready at: {output_path}")
                self.terminal_output.append("===================================")

        # Start the first step
        process_step(0)

    def check_class_distribution(self):
        """Check class distribution in the selected CSV file."""
        # Get the CSV file path from input
        file_path = self.csv_input.text()

        # Step 1: Check if a file is selected
        if not file_path:
            QMessageBox.warning(self, "Input Error", "Please select a CSV file first.")
            return

        # Step 2: Verify the file extension is .csv
        if not file_path.endswith(".csv"):
            QMessageBox.warning(self, "File Error", "The selected file must be a CSV.")
            return

        try:
            # Step 3: Read the CSV file
            df = pd.read_csv(file_path)

            # Step 4: Check if the 'fire_occurred' column exists
            if 'Fire_Occurred' not in df.columns:
                QMessageBox.critical(self, "Missing Column", "The file must contain a 'fire_occurred' column.")
                return

            # Step 5: Calculate class distribution
            class_counts = df['Fire_Occurred'].value_counts()
            num_zeros = class_counts.get(0.0, 0)
            num_ones = class_counts.get(1.0, 0)

            # Step 6: Display the class distribution
            self.terminal_output.append("===================================")
            self.terminal_output.append("CLASS DISTRIBUTION")
            self.terminal_output.append("===================================")
            self.terminal_output.append(f"Number of 0.0's (No Fire): {num_zeros}")
            self.terminal_output.append(f"Number of 1.0's (Fire Occurred): {num_ones}")
            self.terminal_output.append("===================================")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while reading the file:\n{str(e)}")
            self.terminal_output.append(f"Error reading file: {str(e)}")

    def balance_data(self):
        """Balance the dataset using the selected technique and sampling ratio."""
        from imblearn.over_sampling import SMOTE
        from imblearn.under_sampling import NearMiss
        from imblearn.combine import SMOTEENN
        import pandas as pd
        from PyQt5.QtWidgets import QMessageBox

        # Get file path
        file_path = self.csv_input.text()
        if not file_path:
            QMessageBox.warning(self, "Input Error", "Please select a CSV file first.")
            return

        # Read the sampling ratio and technique
        sampling_ratio = self.sampling_ratio_dropdown.currentText()
        sampling_ratio_value = float(sampling_ratio.strip('%')) / 100
        balance_technique = self.balance_dropdown.currentText()

        if not file_path.endswith('.csv'):
            QMessageBox.warning(self, "File Error", "The selected file must be a CSV.")
            return

        try:
            # Step 1: Load dataset
            df = pd.read_csv(file_path)

            # Ensure 'fire_occurred' column exists
            if 'fire_occurred' not in df.columns:
                QMessageBox.critical(self, "Missing Column", "The file must contain a 'fire_occurred' column.")
                return

            self.terminal_output.append(f"Balancing dataset using {balance_technique} with {sampling_ratio} sampling ratio...")

            # Step 2: Handle date column separately
            if 'date' in df.columns:
                df['date_ordinal'] = pd.to_datetime(df['date']).apply(lambda x: x.toordinal())
                df = df.drop(columns=['date'])  # Drop original date column

            # Step 3: Prepare features (X) and target (y)
            X = df.drop(columns=['fire_occurred'])  # Features
            y = df['fire_occurred']               # Target

            # Ensure all features are numeric
            X = X.select_dtypes(include=[float, int, np.number])

            # Step 4: Apply balancing technique
            if balance_technique == "SMOTE":
                resampler = SMOTE(sampling_strategy=sampling_ratio_value, random_state=42)
            elif balance_technique == "NearMiss-3":
                resampler = NearMiss(version=3)
            elif balance_technique == "SMOTE+ENN":
                resampler = SMOTEENN(sampling_strategy=sampling_ratio_value, random_state=42)
            else:
                QMessageBox.warning(self, "Invalid Technique", "Selected balancing technique is not supported.")
                return

            # Resample the dataset
            X_resampled, y_resampled = resampler.fit_resample(X, y)

            # Step 5: Restore date column if applicable
            if 'date_ordinal' in df.columns:
                X_resampled['date'] = X_resampled['date_ordinal'].apply(lambda x: pd.Timestamp.fromordinal(int(x)))
                X_resampled = X_resampled.drop(columns=['date_ordinal'])

            # Combine resampled features and target
            balanced_df = X_resampled.copy()
            balanced_df['fire_occurred'] = y_resampled

            # Step 6: Save the balanced dataset
            output_path = file_path.replace(".csv", "_balanced.csv")
            balanced_df.to_csv(output_path, index=False)

            self.terminal_output.append("===================================")
            self.terminal_output.append("DATASET BALANCED SUCCESSFULLY")
            self.terminal_output.append(f"Balanced dataset saved to: {output_path}")
            self.terminal_output.append("===================================")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred:\n{str(e)}")
            self.terminal_output.append(f"Error balancing data: {str(e)}")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = ForestFireApp()
    window.show()
    sys.exit(app.exec_())
