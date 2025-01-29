# ui/main_window.py

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel,
    QLineEdit, QPushButton, QComboBox, QMessageBox, QTextEdit
)
from PyQt5.QtCore import Qt
from datetime import datetime
import json
import geopandas as gpd
import os
import subprocess
from pathlib import Path

# Import backend modules
from modules.credentials_manager import load_or_update_credentials, save_credentials
from modules.climate_data_fetcher import fetch_climate_data

class CustomOutput:
    """Redirect stdout to the QTextEdit widget."""
    def __init__(self, text_edit_widget):
        self.text_edit_widget = text_edit_widget

    def write(self, message):
        if message.strip() != "":
            self.text_edit_widget.append(message)

    def flush(self):
        pass  # Required for compatibility with sys.stdout

class ForestFireApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Forest Fire Dataset Generation Tool")
        self.setGeometry(100, 100, 800, 700)

        self.initUI()
        
        # Redirect stdout to the terminal box
        sys.stdout = CustomOutput(self.terminal_output)

        # Load credentials if they exist
        self.credentials = self.load_credentials_on_startup()

    def initUI(self):
        # Central widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout()

        # Input fields and labels
        self.start_date_label = QLabel("Enter Start Date (YYYY-MM-DD):")
        self.start_date_input = QLineEdit()

        self.end_date_label = QLabel("Enter End Date (YYYY-MM-DD):")
        self.end_date_input = QLineEdit()

        self.province_label = QLabel("Select Province:")
        self.province_combo = QComboBox()
        self.provinces = [
            "Alberta", "British Columbia", "Manitoba", "New Brunswick", "Newfoundland and Labrador",
            "Northwest Territories", "Nova Scotia", "Nunavut", "Ontario", "Prince Edward Island",
            "Quebec", "Saskatchewan", "Yukon"
        ]
        self.province_combo.addItems(self.provinces)

        self.credentials_label = QLabel("Copernicus Credentials")
        self.username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        self.password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        self.save_credentials_button = QPushButton("Save Credentials")
        self.save_credentials_button.clicked.connect(self.save_credentials)

        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_tool)

        # Terminal output box
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setStyleSheet("background-color: black; color: white; font-family: monospace;")
        self.terminal_output.setMinimumHeight(200)

        # Add widgets to layout
        layout.addWidget(self.start_date_label)
        layout.addWidget(self.start_date_input)
        layout.addWidget(self.end_date_label)
        layout.addWidget(self.end_date_input)
        layout.addWidget(self.province_label)
        layout.addWidget(self.province_combo)
        layout.addWidget(self.credentials_label)
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.save_credentials_button)
        layout.addWidget(self.run_button)
        layout.addWidget(QLabel("Terminal Output:"))
        layout.addWidget(self.terminal_output)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def load_credentials_on_startup(self):
        credentials_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "credentials", "credentials.json")
        if os.path.exists(credentials_path):
            credentials = load_or_update_credentials(credentials_path)
            if credentials:
                self.username_input.setText(credentials.get("username", ""))
                self.password_input.setText(credentials.get("password", ""))
                return credentials
        else:
            QMessageBox.warning(self, "Credentials Missing", "No Copernicus credentials found. Please enter them before running the tool.")
            return None

    def save_credentials(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Input Error", "Both username and password must be provided.")
            return

        credentials_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "credentials", "credentials.json")
        save_credentials(credentials_path, username, password)

        QMessageBox.information(self, "Success", "Credentials saved successfully.")
        self.credentials = {"username": username, "password": password}

    def run_tool(self):
        if not self.credentials:
            QMessageBox.warning(self, "Credentials Missing", "Please save Copernicus credentials before running the tool.")
            return

        start_date = self.start_date_input.text().strip()
        end_date = self.end_date_input.text().strip()
        province = self.province_combo.currentText()

        if not start_date or not end_date:
            QMessageBox.warning(self, "Input Error", "Start and End dates must be provided.")
            return

        # Validate date formats
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            if start_dt > end_dt:
                QMessageBox.warning(self, "Input Error", "Start date must be before or equal to End date.")
                return
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Dates must be in YYYY-MM-DD format.")
            return

        # Define directories using pathlib for cross-platform compatibility
        base_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent
        data_folder = base_dir / "data"
        climate_folder = data_folder / "climate"
        grid_folder = data_folder / "grid" / province
        output_folder = base_dir / "output" / "requests"

        os.makedirs(climate_folder, exist_ok=True)
        os.makedirs(output_folder, exist_ok=True)

        # Assume grid is already created and available
        grid_shapefile = data_folder / "grid" / province / f"{province}_Grid.shp"
        if not grid_shapefile.exists():
            QMessageBox.warning(self, "Grid File Missing", f"Grid shapefile for {province} not found at {grid_shapefile}.")
            return

        # Generate a unique request directory based on timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        request_dir = output_folder / f"request_{timestamp}"
        subdirs = ["Climate"]
        for sub in subdirs:
            (request_dir / sub).mkdir(parents=True, exist_ok=True)

        # Extract bounding box from the grid shapefile
        try:
            gdf = gpd.read_file(grid_shapefile)
            bounding_box = list(gdf.total_bounds)  # [minx, miny, maxx, maxy]
        except Exception as e:
            QMessageBox.warning(self, "Shapefile Error", f"Failed to read shapefile: {e}")
            return

        # Extract year and months from start_date and end_date
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            year = start_dt.year
            # Handle multiple years if needed
            months = list(range(start_dt.month, end_dt.month + 1)) if start_dt.year == end_dt.year else list(range(1, 13))
        except Exception as e:
            QMessageBox.warning(self, "Date Error", f"Error processing dates: {e}")
            return

        # Paths for backend modules
        credentials_path = data_folder / "credentials" / "credentials.json"
        access_token_path = data_folder / "credentials" / "access_token.json"

        # Step 1: Fetch Climate Data
        fetch_climate_data(bounding_box, start_date, end_date, str(request_dir / "Climate"))

        QMessageBox.information(self, "Success", f"Climate data processing completed.\nOutput saved to: {request_dir / 'Climate'}")

        print(f"[UI] Climate data processing completed for request {timestamp}.")

        # Placeholder for further steps
        # Future Steps: Fire History, NDVI, Topo, Merging

def main():
    app = QApplication(sys.argv)
    main_window = ForestFireApp()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
