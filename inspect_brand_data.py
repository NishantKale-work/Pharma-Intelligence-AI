
from pathlib import Path
import pandas as pd

project_dir = Path(__file__).resolve().parent

possible_paths = [
    project_dir / "IMS_Brand_Analysis.csv",
    project_dir.parent / "IMS_Brand_Analysis.csv",
]

file_path = next(
    (path for path in possible_paths if path.exists()),
    None
)

if file_path is None:
    print("CSV file not found. Checked:")
    for path in possible_paths:
        print(path)
    raise FileNotFoundError(
        "Move the script to the correct project or update the file path."
    )

df = pd.read_csv(file_path, nrows=5)

print("FILE FOUND:", file_path)
print("\nCOLUMN NAMES:")
print(df.columns.tolist())

print("\nSAMPLE RECORDS:")
print(df.to_string(index=False))
