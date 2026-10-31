# Setup Guide

This guide explains how to configure and run the Pharma Intelligence AI Platform locally.

## 1. Prerequisites

Install the following:

- **Python 3.10 or newer**
- **Git**
- **Ollama** for local LLM inference
- Authorized IMS pharmaceutical market datasets required by the application

Check Python and Git:

```powershell
python --version
git --version
```

## 2. Clone the repository

```powershell
git clone https://github.com/NishantKale-work/Pharma-Intelligence-AI.git
cd Pharma-Intelligence-AI
```

> The repository is currently private. You must have GitHub access to clone it.

## 3. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can use the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

## 4. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

For development and tests:

```powershell
pip install -r requirements-dev.txt
```

## 5. Configure the IMS datasets

The application expects authorized IMS data files. They are not included in this repository.

By default, the application looks for data in the **parent directory of the project folder**.

Expected files include:

```text
IMS_Company_Analysis.csv
IMS_Company_Group_Analysis.csv
IMS_Company_Value_Unit_Analysis.csv
IMS_Group_Analysis.csv
```

For a local Windows setup, the directory structure may look like:

```text
PythonProject/
├── IMS_Company_Analysis.csv
├── IMS_Company_Group_Analysis.csv
├── IMS_Company_Value_Unit_Analysis.csv
├── IMS_Group_Analysis.csv
└── Pharma-Intelligence-AI/
    ├── dashboard.py
    ├── app/
    └── ...
```

The data must have the column structure expected by the analytics modules. Different IMS extracts may require data preparation before they can be used.

### Optional: Set a custom data directory

Set `IMS_DATA_DIR` to the folder containing the authorized datasets:

```powershell
$env:IMS_DATA_DIR = "C:\path\to\your\ims-data"
```

This setting applies to the current PowerShell session.

## 6. Configure Ollama

Install Ollama from:

https://ollama.com/

Start Ollama, then pull the default model:

```powershell
ollama pull llama3.2:3b
```

Verify that the model is available:

```powershell
ollama list
```

The application defaults to:

```text
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2:3b
OLLAMA_BASE_URL=http://localhost:11434
```

These values can be overridden with environment variables.

For example:

```powershell
$env:LLM_PROVIDER = "ollama"
$env:OLLAMA_MODEL = "llama3.2:3b"
$env:OLLAMA_BASE_URL = "http://localhost:11434"
```

Ollama must be running locally before using LLM-powered investigation features.

## 7. Run the dashboard

From the project root:

```powershell
python -m streamlit run dashboard.py
```

Streamlit should open the application in your browser. If it does not, use the local URL printed in the terminal, usually:

http://localhost:8501

## 8. Run tests

```powershell
python -m pytest
```

The repository includes deterministic tests for selected data, analytics, and agent behaviors. Passing these tests does not guarantee that every LLM response is factually accurate or that every external dataset is complete.

## Troubleshooting

### Missing IMS data

Check that the required CSV files exist in the configured data directory and that `IMS_DATA_DIR`, if set, points to the correct folder.

### Ollama connection error

Confirm that Ollama is installed and running:

```powershell
ollama list
```

Check that `OLLAMA_BASE_URL` matches the local Ollama endpoint.

### Model not found

Pull the configured model:

```powershell
ollama pull llama3.2:3b
```

If you configure a different model, make sure it is available in Ollama and update `OLLAMA_MODEL`.

### Dependency or import errors

Activate the virtual environment and reinstall the project dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Data and confidentiality

Use only datasets you are authorized to access. Do not commit proprietary IMS data, credentials, internal company information, or confidential outputs to GitHub.