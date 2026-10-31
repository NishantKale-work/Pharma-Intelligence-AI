# Pharma Intelligence AI — Investigation Chat

## Overview

The Investigation Chat connects the Streamlit dashboard to the Pharma Intelligence AI commercial analysis agent.

It allows users to ask commercial questions using the available IMS datasets and analytical modules.

## Run the dashboard

1. Back up your current `dashboard.py`.
2. Ensure the project dependencies are installed.
3. From the `Pharma_Intelligence_AI` project directory, run:

   ```powershell
   python -m py_compile dashboard.py
   python -m streamlit run dashboard.py