# Pharma Commercial Intelligence Dashboard

## 1. Install dashboard dependencies

Run from the `Pharma_Intelligence_AI` project directory
in the active virtual environment:

```powershell
python -m pip install -r requirements-dashboard.txt

## 2. Start the dashboard

```powershell
python -m streamlit run dashboard.py
```

Streamlit will print a local URL (usually `http://localhost:8501`) to open in your browser.

## 3. Dataset locations

The existing analytics modules expect the four CSV files one folder above `Pharma_Intelligence_AI`, alongside the project folder:

- `IMS_Company_Analysis.csv`
- `IMS_Company_Group_Analysis.csv`
- `IMS_Company_Value_Unit_Analysis.csv`
- `IMS_Group_Analysis.csv`

The dashboard reads these datasets and does not edit them.

## 4. What's included

- Company and competitor selection
- Market vs company growth KPIs
- Market-share and unit-growth indicators
- Therapeutic-group growth-gap ranking and CSV export
- Competitor scorecard and growth/share scatter plot
- Evidence, hypotheses, limitations and data-source tabs
- Tests for the dashboard data layer

The dashboard reports observed associations and benchmark comparisons. It does not claim causal attribution. RAG files are not changed by this upgrade.
