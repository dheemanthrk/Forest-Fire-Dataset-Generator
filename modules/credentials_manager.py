# modules/credentials_manager.py

import json
import os
from typing import Optional

def load_or_update_credentials(credentials_path: str) -> Optional[dict]:
    """
    Loads existing credentials or prompts user to enter them if not found.
    """
    if os.path.exists(credentials_path):
        with open(credentials_path, "r") as file:
            try:
                credentials = json.load(file)
                return credentials
            except json.JSONDecodeError:
                print("[credentials_manager.py] ERROR: Credentials file is not valid JSON.")
                return None
    else:
        # Placeholder: In a real application, you'd collect credentials securely
        print("[credentials_manager.py] Credentials file not found.")
        return None

def save_credentials(credentials_path: str, username: str, password: str) -> None:
    """
    Saves credentials to a JSON file.
    """
    credentials = {
        "username": username,
        "password": password
    }
    with open(credentials_path, "w") as file:
        json.dump(credentials, file)
    print(f"[credentials_manager.py] Credentials saved to {credentials_path}.")
