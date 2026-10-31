# Pharma Intelligence AI Platform

An AI-powered pharmaceutical market intelligence and forecasting platform that combines pharmaceutical market data, commercial analytics, and a multi-agent AI system to support evidence-based commercial decision-making.

> **Project status:** Active development  
> **Application:** Streamlit  
> **Core stack:** Python, Pandas, Plotly, Streamlit, LLM integration

## Overview

Pharma Intelligence AI is designed to help pharmaceutical commercial teams explore market performance, understand company and therapeutic-group trends, investigate growth or decline, and generate structured commercial insights.

The platform combines deterministic analytics with AI-assisted investigation. Python-based calculations provide the analytical evidence, while specialized agents help interpret questions, coordinate analysis, and present findings in a more accessible format.

The project is being developed as a portfolio project demonstrating the application of data analytics, pharmaceutical domain knowledge, and AI engineering to a commercial healthcare use case.

## Key capabilities

### Pharmaceutical market intelligence
- Explore pharmaceutical market performance using IMS market data.
- Analyze company, brand, and therapeutic-group performance.
- Examine market-share movements and commercial trends.
- Compare performance across available market dimensions.

### Commercial analytics
- Identify potential growth drivers and declining segments.
- Decompose market growth across therapeutic groups.
- Investigate company performance and market-share changes.
- Support commercial diagnosis with calculated analytical evidence.

### Multi-agent AI investigation
- Route user questions to relevant commercial analysis workflows.
- Coordinate specialized agents for different analytical tasks.
- Combine analytical outputs into a structured response.
- Use Python-calculated evidence to support quantitative conclusions.

### Interactive dashboard
- Explore market intelligence through a Streamlit interface.
- Review charts, performance indicators, and commercial analysis.
- Use the Investigation Chat to ask questions about supported analyses.

## Architecture

The platform follows a modular structure:

```text
Pharma Intelligence AI
│
├── Streamlit Dashboard
│   ├── Market Intelligence
│   ├── Commercial Analysis
│   └── Investigation Chat
│
├── Multi-Agent Commercial Intelligence
│   ├── Commercial Coordinator
│   ├── Commercial Diagnosis
│   ├── Company Analysis
│   ├── Company Deep Dive
│   ├── Market Share Analysis
│   ├── Market Growth Decomposition
│   ├── Therapeutic Group Decomposition
│   └── Commercial Strategy
│
├── Analytics and Data Processing
│   ├── Data Quality
│   ├── Metric Calculations
│   └── Evidence Preparation
│
└── Data and LLM Integration
    ├── IMS Market Data
    └── Configured LLM Service
```

## Technology stack

| Area | Technologies |
|---|---|
| Programming | Python |
| Data processing | Pandas |
| Visualization | Plotly |
| Dashboard | Streamlit |
| AI orchestration | Custom multi-agent architecture |
| LLM integration | Configurable LLM client |
| Testing | Pytest |
| Development | PyCharm, Git, Docker |

## Repository structure

```text
Pharma_Intelligence_AI/
├── app/
│   ├── agents/
│   ├── api/
│   ├── core/
│   ├── llm/
│   ├── dashboard_data.py
│   └── main.py
├── Evaluation/
│   └── evaluate_answer_quality.py
├── tests/
├── dashboard.py
├── requirements.txt
├── requirements-dev.txt
├── dockerfile
├── .dockerignore
├── .gitignore
├── SETUP.md
└── DEMO.md
```

## Getting started

See **[SETUP.md](SETUP.md)** for environment setup, dependencies, data configuration, and application launch instructions.

## Demo walkthrough

See **[DEMO.md](DEMO.md)** for a guided walkthrough of the dashboard and commercial investigation workflow.

## Data and access

The platform uses IMS pharmaceutical market data for its analyses. The underlying datasets are **not included in this public repository** because they may be subject to licensing, confidentiality, or access restrictions.
To run the application with real data, users must provide appropriately authorized datasets and configure the required LLM service.

## Evaluation

The repository includes deterministic evaluation checks for selected agent and analytical behaviors, including:

- Intent routing
- Parameter extraction
- Numeric conversion
- Metric recalculation
- JSON-safe output handling

These checks validate selected deterministic behaviors. They do **not** establish the factual accuracy of all LLM-generated responses or the completeness of live market data.

## Current limitations

- Application functionality depends on the availability and structure of the required market datasets.
- LLM-assisted responses depend on the configured model and service.
- The project is under active development; not all workflows have been validated for production use.
- Evaluation coverage is focused on selected deterministic behaviors and should be expanded with broader integration and answer-quality testing.

## Author

**Nishant Kale**  
Pharmaceutical Management | Pharma Commercial Analytics | AI Engineering

[GitHub Repository](https://github.com/NishantKale-work/Pharma-Intelligence-AI)
