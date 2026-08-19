"""
Pulls sample wheat production data from USDA NASS Quick Stats API
and saves it locally as a CSV for Agent 1 to use later.
"""

import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()  # reads .env file in project root

API_KEY = os.getenv("NASS_API_KEY")
BASE_URL = "https://quickstats.nass.usda.gov/api/api_GET/"

def pull_wheat_data(year=2023, state="KANSAS"):
    params = {
        "key": API_KEY,
        "commodity_desc": "WHEAT",
        "year": year,
        "state_name": state,
        "agg_level_desc": "STATE",
        "format": "JSON",
    }

    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()

    data = response.json()
    records = data.get("data", [])

    if not records:
        print("No records found. Try a different year/state/commodity.")
        return None

    df = pd.DataFrame(records)
    print(f"Pulled {len(df)} records.")
    print(df.head())

    output_path = "data/raw/wheat_kansas_2023.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

    return df

if __name__ == "__main__":
    pull_wheat_data()