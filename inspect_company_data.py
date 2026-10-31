
from pathlib import Path
import pandas as pd

# Use the parent folder containing Pharma_Intelligence_AI.
DATA_FOLDER = Path(__file__).resolve().parent.parent

print("Looking for data in:", DATA_FOLDER)

files = [
    "IMS_Company_Analysis.csv",
    "IMS_Company_Group_Analysis.csv",
    "IMS_Company_Value_Unit_Analysis.csv",
    "IMS_Market_Forecast_Summary.csv",
    "IMS_Final_12M_Forecast.csv",
]

for filename in files:
    path = DATA_FOLDER / filename

    print("\n" + "=" * 60)
    print("FILE:", filename)
    print("PATH:", path)
    print("EXISTS:", path.exists())

    if path.exists():
        df = pd.read_csv(path)
        print("ROWS:", len(df))
        print("COLUMNS:", df.columns.tolist())
        print("\nFIRST 3 ROWS:")
        print(df.head(3).to_string(index=False))
