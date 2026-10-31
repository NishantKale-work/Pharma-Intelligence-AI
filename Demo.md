# Demo Guide

## Pharma Intelligence AI Platform

This walkthrough demonstrates how the platform can support pharmaceutical commercial market analysis and AI-assisted investigation.

**Suggested duration:** 3–5 minutes

## Demo prerequisites

Before starting:

- The dashboard is running locally.
- Authorized IMS datasets are configured.
- Ollama is running and the configured model is available.
- The selected company exists in the loaded dataset.

Launch the application:

```powershell
python -m streamlit run dashboard.py
```

## Demo flow

### 1. Introduce the business problem

Pharmaceutical commercial teams work with large market datasets and need to understand:

- How a company is performing relative to the market
- Which therapeutic groups may be contributing to growth or decline
- How market share is changing
- Which areas deserve further commercial investigation

The platform brings selected analyses and AI-assisted investigation into one interface.

### 2. Explore the dashboard

Open the Streamlit dashboard and review the available market intelligence views.

Show:

- The selected company
- The configured market period
- Company performance metrics
- Market growth and share indicators
- Therapeutic-group analysis
- Competitor comparisons, where available

Explain that the quantitative metrics are calculated through Python analytics using the configured data.

### 3. Investigate a company

Select a company available in the dataset. The current default company is:

```text
ALKEM*
```

Review its performance and compare it with the market and selected competitors.

Discuss the distinction between:

- **Verified facts:** values calculated from the underlying dataset
- **Interpretations or hypotheses:** possible explanations that require further validation
- **Priority investigations:** follow-up questions suggested by the analysis

### 4. Demonstrate Investigation Chat

Use the Investigation Chat to ask a question supported by the available commercial analysis.

Example questions:

```text
Why is this company growing slower than the market?
```

```text
Which therapeutic groups are contributing positively or negatively?
```

```text
How has the company's market share changed?
```

The system routes supported questions through its commercial analysis workflow and uses the resulting evidence to generate a structured response.

The exact response depends on the configured datasets, model, and supported analysis.

### 5. Explain the multi-agent design

Describe the system at a high level:

1. The commercial coordinator interprets the investigation workflow.
2. Specialized analysis components examine relevant commercial dimensions.
3. Python analytics calculate quantitative evidence.
4. The system combines available evidence into a structured commercial response.

The goal is to combine deterministic calculations with AI-assisted interpretation—not to rely on the language model alone for numerical analysis.

## What this demo demonstrates

- Pharmaceutical domain problem framing
- Data processing and commercial analytics
- Interactive dashboard development
- Modular multi-agent architecture
- Local LLM integration
- Evidence-oriented AI application design

## Demo limitations

- Results depend on the configured IMS datasets.
- The repository does not include the underlying licensed market data.
- LLM-generated interpretations should be reviewed and validated.
- This portfolio project is under active development and is not represented as a production-validated commercial decision system.

## Suggested interview summary

> I built a Pharma Intelligence AI Platform that combines pharmaceutical market analytics with a multi-agent AI investigation workflow. The dashboard helps explore company and therapeutic-group performance, while specialized agents coordinate commercial analyses. I designed the system so quantitative evidence is calculated through Python and then used to support AI-assisted interpretation. The project demonstrates how pharmaceutical domain knowledge, analytics, and AI engineering can be integrated into a practical commercial intelligence use case.