"""Polished Streamlit UI for Pharma Commercial Intelligence AI.

Run from the project root:
    python -m streamlit run dashboard.py
"""
from __future__ import annotations

import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.dashboard_data import available_companies, build_dashboard_payload
from app.agents.agent import run_agent

st.set_page_config(
    page_title="Pharma Commercial Intelligence",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Warm ivory, charcoal, muted forest green, sage and restrained amber.
IVORY = "#201A17"
CHARCOAL = "#E8E0D6"
FOREST = "#C49A72"
SAGE = "#49382E"
AMBER = "#9C7655"
CORAL = "#C97868"
MUTED = "#B8A99B"
GRID = "#49382E"
BRONZE_DARK = "#8C6A4F"

st.markdown(
    f"""
    <style>
      :root {{
        --pci-ivory: {IVORY};
        --pci-charcoal: {CHARCOAL};
        --pci-forest: {FOREST};
        --pci-sage: {SAGE};
        --pci-amber: {AMBER};
        --pci-coral: {CORAL};
      }}

      html, body, [data-testid="stAppViewContainer"], .stApp {{
        background: {IVORY} !important;
        color: {CHARCOAL};
      }}

      [data-testid="stMain"], [data-testid="stMainBlockContainer"] {{
        background: {IVORY};
        color: {CHARCOAL};
      }}

      [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] {{
        color: {CHARCOAL};
      }}

      /* Warm, dark native controls and chat surfaces */
      [data-baseweb="select"] > div,
      [data-baseweb="input"] > div,
      [data-baseweb="textarea"] > div,
      [data-testid="stChatInput"] textarea {{
        background: #30251F !important;
        color: #E8E0D6 !important;
        border-color: #5A4537 !important;
      }}

      /* Visible chat composer and send button on dark theme. */
      [data-testid="stChatInput"] {{
        background: #30251F !important;
        border: 1px solid #7A5A40 !important;
        border-radius: 10px !important;
      }}
      [data-testid="stChatInput"] button {{
        background: #C49A72 !important;
        color: #201A17 !important;
        border: 1px solid #C49A72 !important;
        opacity: 1 !important;
        visibility: visible !important;
      }}
      [data-testid="stChatInput"] button svg {{
        color: #201A17 !important;
        fill: #201A17 !important;
        stroke: #201A17 !important;
        opacity: 1 !important;
        visibility: visible !important;
      }}
      [data-testid="stChatInput"] button:disabled {{
        background: #7A5A40 !important;
        color: #E8E0D6 !important;
        opacity: 1 !important;
      }}
      .js-plotly-plot .plotly text {{
        fill: #D2BFAE !important;
      }}

      [data-testid="stChatMessage"] {{
        background: #30251F;
        border: 1px solid #49382E;
        border-radius: 12px;
        padding: .75rem 1rem;
      }}

      [data-testid="stExpander"] {{
        background: #30251F;
        border: 1px solid #49382E;
        border-radius: 10px;
      }}

      [data-testid="stDataFrame"], [data-testid="stTable"] {{
        background: #30251F;
        color: #E8E0D6;
      }}

      .stMarkdown, label, p, li, h1, h2, h3, h4, h5, h6 {{
        color: inherit;
      }}

      button[kind="secondary"], [data-testid="stBaseButton-secondary"] {{
        background: #30251F;
        color: #E8E0D6;
        border: 1px solid #5A4537;
      }}

      button[kind="secondary"]:hover, [data-testid="stBaseButton-secondary"]:hover {{
        border-color: {AMBER};
        color: #F2D8BC;
      }}

      /* Keep Streamlit's fixed chat composer and its footer dark too. */
      [data-testid="stBottom"],
      [data-testid="stBottom"] > div,
      [data-testid="stChatInput"],
      [data-testid="stChatInput"] > div,
      [data-testid="stChatInput"] form {{
        background: #201A17 !important;
        border-color: #49382E !important;
        box-shadow: none !important;
      }}

      [data-testid="stChatInput"] textarea,
      [data-testid="stChatInput"] textarea::placeholder {{
        color: #E8E0D6 !important;
        -webkit-text-fill-color: #E8E0D6 !important;
        opacity: 1 !important;
      }}

      [data-testid="stSidebar"] {{
        background: #201A17 !important;
      }}

      [data-testid="stHeader"] {{
        background: rgba(32,26,23,.96) !important;
      }}

      .block-container {{
        padding-top: 1.4rem;
        padding-bottom: 3rem;
        max-width: 1500px;
      }}

      section[data-testid="stSidebar"] {{
        background: #261E19;
        border-right: 1px solid #49382E;
      }}

      /* Explicit high-contrast text: avoid inherited near-black labels on dark panels. */
      [data-testid="stAppViewContainer"],
      [data-testid="stMain"],
      [data-testid="stMainBlockContainer"] {{
        color: #E8E0D6 !important;
      }}

      [data-testid="stAppViewContainer"] .stMarkdown,
      [data-testid="stAppViewContainer"] .stMarkdown p,
      [data-testid="stAppViewContainer"] .stMarkdown li,
      [data-testid="stAppViewContainer"] .stMarkdown span,
      [data-testid="stAppViewContainer"] label,
      [data-testid="stAppViewContainer"] [data-testid="stWidgetLabel"],
      [data-testid="stAppViewContainer"] [data-testid="stWidgetLabel"] p,
      [data-testid="stAppViewContainer"] h1,
      [data-testid="stAppViewContainer"] h2,
      [data-testid="stAppViewContainer"] h3,
      [data-testid="stAppViewContainer"] h4,
      [data-testid="stAppViewContainer"] h5,
      [data-testid="stAppViewContainer"] h6 {{
        color: #E8E0D6 !important;
        -webkit-text-fill-color: #E8E0D6;
      }}

      section[data-testid="stSidebar"] {{
        color: #E8E0D6 !important;
      }}

      section[data-testid="stSidebar"] * {{
        color: #E8E0D6;
      }}

      section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
      section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
      section[data-testid="stSidebar"] label {{
        color: #B8A99B !important;
        -webkit-text-fill-color: #B8A99B;
        font-weight: 650;
      }}

      /* Selectbox/input: dark fill plus readable selected value, placeholder and icons. */
      [data-baseweb="select"] > div,
      [data-baseweb="input"] > div,
      [data-baseweb="textarea"] > div {{
        background: #30251F !important;
        border: 1px solid #5A4537 !important;
        border-radius: 9px !important;
      }}

      [data-baseweb="select"] *,
      [data-baseweb="input"] *,
      [data-baseweb="textarea"] *,
      [data-baseweb="popover"] *,
      [role="listbox"] *,
      [role="option"] {{
        color: #E8E0D6 !important;
        -webkit-text-fill-color: #E8E0D6 !important;
      }}

      [data-baseweb="select"] input {{
        color: #E8E0D6 !important;
        -webkit-text-fill-color: #E8E0D6 !important;
      }}

      [data-baseweb="select"] svg {{
        fill: #C49A72 !important;
        color: #C49A72 !important;
      }}

      [data-baseweb="popover"] ul,
      [role="listbox"] {{
        background: #30251F !important;
        border: 1px solid #5A4537 !important;
      }}

      [role="option"]:hover,
      [aria-selected="true"] {{
        background: #49382E !important;
      }}

      /* High-specificity rules for Streamlit selectboxes (company + competitors).
         BaseWeb often applies its own white background and muted value color. */
      section[data-testid="stSidebar"] div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
      section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] [data-baseweb="select"] > div {{
        background-color: #30251F !important;
        border: 1px solid #7A5A40 !important;
      }}

      section[data-testid="stSidebar"] div[data-testid="stSelectbox"] [data-baseweb="select"] span,
      section[data-testid="stSidebar"] div[data-testid="stSelectbox"] [data-baseweb="select"] input,
      section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] [data-baseweb="select"] span,
      section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] [data-baseweb="select"] input {{
        color: #F3E8DC !important;
        -webkit-text-fill-color: #F3E8DC !important;
        opacity: 1 !important;
      }}

      section[data-testid="stSidebar"] div[data-testid="stSelectbox"] [data-baseweb="select"] svg,
      section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] [data-baseweb="select"] svg {{
        color: #C49A72 !important;
        fill: #C49A72 !important;
      }}

      /* Force the actual BaseWeb control surface to stay dark.
         Do not apply transparent backgrounds to every nested div: that can
         expose Streamlit/BaseWeb's default white selectbox surface. */
      section[data-testid="stSidebar"] div[data-testid="stSelectbox"] [data-baseweb="select"],
      section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] [data-baseweb="select"] {{
        background: #30251F !important;
        border-radius: 9px !important;
      }}

      section[data-testid="stSidebar"] div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
      section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] [data-baseweb="select"] > div {{
        background: #30251F !important;
        background-color: #30251F !important;
        border: 1px solid #7A5A40 !important;
        border-radius: 9px !important;
        box-shadow: none !important;
      }}

      section[data-testid="stSidebar"] div[data-testid="stSelectbox"] [data-baseweb="select"] [data-testid],
      section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] [data-baseweb="select"] [data-testid] {{
        color: #F3E8DC !important;
        -webkit-text-fill-color: #F3E8DC !important;
      }}

      section[data-testid="stSidebar"] div[data-testid="stSelectbox"] [data-baseweb="select"] input,
      section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] [data-baseweb="select"] input {{
        color: #F3E8DC !important;
        -webkit-text-fill-color: #F3E8DC !important;
        caret-color: #F3E8DC !important;
      }}

      section[data-testid="stSidebar"] div[data-testid="stSelectbox"] [data-baseweb="select"] svg,
      section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] [data-baseweb="select"] svg {{
        color: #C49A72 !important;
        fill: #C49A72 !important;
      }}

      /* Dropdown menu rendered in a portal outside the sidebar DOM. */
      [data-baseweb="popover"] [role="listbox"],
      [data-baseweb="popover"] ul {{
        background: #30251F !important;
        border: 1px solid #7A5A40 !important;
      }}

      [data-baseweb="popover"] [role="option"],
      [data-baseweb="popover"] [role="option"] * {{
        background: #30251F !important;
        color: #F3E8DC !important;
        -webkit-text-fill-color: #F3E8DC !important;
      }}

      [data-baseweb="popover"] [role="option"]:hover,
      [data-baseweb="popover"] [aria-selected="true"] {{
        background: #49382E !important;
      }}

      /* Style only the primary Run analysis action. */
      section[data-testid="stSidebar"] button[kind="primary"],
      section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {{
        background: #7A5A40 !important;
        color: #E8E0D6 !important;
        -webkit-text-fill-color: #E8E0D6 !important;
        border: 1px solid #7A5A40 !important;
        border-radius: 10px !important;
        font-weight: 750 !important;
        min-height: 46px;
        box-shadow: 0 3px 8px rgba(37, 43, 39, .12);
        transition: background .15s ease, border-color .15s ease, transform .15s ease;
      }}

      section[data-testid="stSidebar"] button[kind="primary"] *,
      section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] * {{
        color: #E8E0D6 !important;
        -webkit-text-fill-color: #E8E0D6 !important;
        font-weight: 750 !important;
      }}

      section[data-testid="stSidebar"] button[kind="primary"]:hover,
      section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:hover {{
        background: {FOREST} !important;
        border-color: {FOREST} !important;
        color: #E8E0D6 !important;
        -webkit-text-fill-color: #E8E0D6 !important;
        box-shadow: 0 4px 10px rgba(37, 43, 39, .16);
      }}

      section[data-testid="stSidebar"] button[kind="primary"]:focus-visible,
      section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:focus-visible {{
        outline: 2px solid {AMBER} !important;
        outline-offset: 3px;
      }}

      section[data-testid="stSidebar"] button[kind="primary"]:disabled,
      section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:disabled {{
        background: #49382E !important;
        border-color: #49382E !important;
        color: #B8A99B !important;
        -webkit-text-fill-color: #B8A99B !important;
        box-shadow: none;
      }}

      section[data-testid="stSidebar"] [role="radiogroup"] label {{
        border-radius: 8px;
        padding: .4rem .55rem;
        margin-bottom: .15rem;
      }}

      .brand-lockup {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin: .1rem 0 1.4rem 0;
      }}

      .brand-mark {{
        width: 42px;
        height: 42px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: {SAGE};
        color: {FOREST};
        font-size: 22px;
        border: 1px solid #5A4537;
      }}

      .brand-title {{
        font-size: 1rem;
        font-weight: 800;
        letter-spacing: .015em;
        color: {CHARCOAL};
        line-height: 1.25;
      }}

      .brand-subtitle {{
        color: #B8A99B;
        font-size: .76rem;
        margin-top: 4px;
      }}

      .hero {{
        background: #30251F;
        border: 1px solid #5A4537;
        border-left: 5px solid {FOREST};
        border-radius: 14px;
        padding: 25px 28px;
        color: #F3E8DC;
        margin: 0 0 20px 0;
        box-shadow: 0 3px 12px rgba(0,0,0,.12);
        position: relative;
      }}

      .hero-eyebrow {{
        color: #C49A72 !important;
        font-size: .72rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: .11em;
      }}

      .hero-title {{
        color: #F3E8DC !important;
        font-size: 1.9rem;
        line-height: 1.2;
        font-weight: 760;
        margin: 8px 0 9px 0;
      }}

      .hero-copy {{
        color: #E0D0C0 !important;
        font-size: .94rem;
        max-width: 900px;
      }}

      .hero-meta {{
        color: #D0BBA7 !important;
        font-size: .79rem;
        margin-top: 15px;
      }}

      .section-kicker {{
        color: #C49A72 !important;
        text-transform: uppercase;
        letter-spacing: .1em;
        font-size: .7rem;
        font-weight: 800;
        margin-bottom: 4px;
      }}

      .section-title {{
        color: #F3E8DC !important;
        font-size: 1.35rem;
        font-weight: 780;
        margin: 0 0 .15rem 0;
      }}

      .section-help {{
        color: #B8A99B !important;
        font-size: .88rem;
        margin-bottom: 1rem;
      }}

      .panel {{
        background: #30251F;
        border: 1px solid #49382E;
        border-radius: 13px;
        padding: 18px 20px;
        box-shadow: 0 2px 8px rgba(37,43,39,.025);
      }}

      .kpi-label {{
        color: #CBB9A8 !important;
        font-size: .8rem;
        font-weight: 650;
        margin-bottom: 8px;
      }}

      .kpi-value {{
        color: #F3E8DC !important;
        font-size: 1.85rem;
        font-weight: 760;
        line-height: 1.15;
        letter-spacing: -.025em;
      }}

      .kpi-foot {{
        color: #CBB9A8 !important;
        font-size: .75rem;
        margin-top: 8px;
      }}

      .status-pill {{
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        font-size: .72rem;
        font-weight: 750;
        background: #3D332B;
        color: #D8C3AC;
      }}

      .status-pill.warn {{
        background: #49382E;
        color: #E0B88D;
      }}

      .insight-card {{
        background: #30251F;
        border: 1px solid #49382E;
        border-left: 4px solid {FOREST};
        border-radius: 10px;
        padding: 15px 17px;
        margin-bottom: 10px;
        box-shadow: 0 2px 7px rgba(37,43,39,.02);
      }}

      .insight-title {{
        color: #F3E8DC !important;
        font-weight: 760;
        margin-bottom: 5px;
      }}

      .insight-copy {{
        color: #D2BFAE;
        font-size: .89rem;
        line-height: 1.55;
      }}

      .muted-note {{
        color: {MUTED};
        font-size: .8rem;
        line-height: 1.5;
      }}

      div[data-testid="stMetric"] {{
        background: #30251F;
        border: 1px solid #49382E;
        padding: 15px 17px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(37,43,39,.025);
      }}

      div[data-testid="stMetricLabel"] p {{
        color: {MUTED};
        font-size: .79rem;
        font-weight: 650;
      }}

      div[data-testid="stMetricValue"] {{
        color: {CHARCOAL};
        font-weight: 760;
      }}

      div[data-testid="stTabs"] button {{
        font-weight: 650;
      }}

      div[data-testid="stDataFrame"] {{
        border: 1px solid #49382E;
        border-radius: 10px;
        overflow: hidden;
      }}

      .stDownloadButton button {{
        border-radius: 8px;
        font-weight: 650;
      }}

      hr {{
        border-color: #49382E;
      }}

      @media (max-width: 800px) {{
        .hero {{
          padding: 20px;
        }}
        .hero-title {{
          font-size: 1.5rem;
        }}
        .block-container {{
          padding-left: 1rem;
          padding-right: 1rem;
        }}
      }}
    </style>
    """,
    unsafe_allow_html=True,
)


def safe_float(value, default=None):
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def fmt_number(value, decimals=2):
    number = safe_float(value)
    return "N/A" if number is None else f"{number:,.{decimals}f}"


def section_header(kicker: str, title: str, help_text: str | None = None):
    st.markdown(
        f'<div class="section-kicker">{kicker}</div>'
        f'<div class="section-title">{title}</div>',
        unsafe_allow_html=True,
    )
    if help_text:
        st.markdown(
            f'<div class="section-help">{help_text}</div>',
            unsafe_allow_html=True,
        )


def kpi_card(label: str, value: str, foot: str = ""):
    st.markdown(
        f'<div class="panel"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-foot">{foot or " "}</div></div>',
        unsafe_allow_html=True,
    )


def style_plot(fig, height=350):
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#30251F",
        font=dict(
            family="Inter, Segoe UI, sans-serif",
            color="#D2BFAE",
            size=12,
        ),
        margin=dict(l=10, r=12, t=25, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        xaxis=dict(showgrid=False, zeroline=False, linecolor=GRID),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID),
    )
    return fig


# ---------------------------------------------------------
# Sidebar / primary navigation
# ---------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="brand-lockup"><div class="brand-mark">🧬</div><div>'
        '<div class="brand-title">PHARMA INTELLIGENCE</div>'
        '<div class="brand-subtitle">Commercial analytics workspace</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<div style='color:{FOREST};font-size:.72rem;font-weight:800;"
        "letter-spacing:.12em;margin-bottom:.45rem'>WORKSPACE</div>",
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigation",
        [
            "Executive overview",
            "Therapeutic groups",
            "Competitor intelligence",
            "Investigation chat",
            "Evidence & methodology",
        ],
        format_func=lambda x: {
            "Executive overview": "◈   Executive overview",
            "Therapeutic groups": "▤   Therapeutic groups",
            "Competitor intelligence": "◎   Competitor intelligence",
            "Investigation chat": "✦   Investigation chat",
            "Evidence & methodology": "✓   Evidence & methodology",
        }[x],
        label_visibility="collapsed",
        key="primary_navigation",
    )

    st.markdown(
        "<div style='height:1px;background:#49382E;margin:1.2rem 0'></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='color:{FOREST};font-size:.72rem;font-weight:800;"
        "letter-spacing:.12em;margin-bottom:.65rem'>ANALYSIS CONTROLS</div>",
        unsafe_allow_html=True,
    )

    try:
        company_options = available_companies()
    except Exception as exc:
        st.error(f"Unable to load company dataset: {exc}")
        st.stop()

    if not company_options:
        st.error("No companies are available in the source dataset.")
        st.stop()

    default_company = "ALKEM*" if "ALKEM*" in company_options else company_options[0]

    selected_company = st.selectbox(
        "Company",
        options=company_options,
        index=company_options.index(default_company),
        key="selected_company_control",
    )

    # Competitors are optional. Never auto-select Sun or Cipla.
    competitor_options = [
        name for name in company_options
        if name != selected_company
    ]

    previous_company = st.session_state.get("_competitor_company")

    # Clear competitor selections when the company changes.
    if previous_company != selected_company:
        st.session_state["competitor_selection_control"] = []
        st.session_state["_competitor_company"] = selected_company

    # Keep only valid selections for the current company.
    st.session_state["competitor_selection_control"] = [
        name
        for name in st.session_state.get("competitor_selection_control", [])
        if name in competitor_options
    ]

    selected_competitors = st.multiselect(
        "Competitors to compare",
        options=competitor_options,
        key="competitor_selection_control",
        help="Optional: select competitors manually. Changing company clears this selection.",
        placeholder="Choose competitors (optional)",
    )

    run_analysis = st.button(
        "↻  Run commercial analysis",
        type="primary",
        use_container_width=True,
    )

    st.markdown(
        "<div style='height:1px;background:#49382E;margin:1.2rem 0'></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='color:#D2BFAE;font-size:.78rem;line-height:1.6'>"
        "Evidence-led analysis of IMS MAT performance. Findings are "
        "investigation signals, not causal proof.</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='color:#B8A99B;font-size:.7rem;margin-top:1rem'>"
        "DATA PERIOD · MAT SEP 2025 / SEP 2024</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------
# Analysis lifecycle
# ---------------------------------------------------------
selection = (selected_company, tuple(selected_competitors))

if "dashboard_selection" not in st.session_state:
    st.session_state.dashboard_selection = None

if "dashboard_payload" not in st.session_state:
    st.session_state.dashboard_payload = None

if (
    run_analysis
    or st.session_state.dashboard_selection != selection
    or st.session_state.dashboard_payload is None
):
    with st.spinner(
        "Coordinating market, company, group and competitor analyses..."
    ):
        try:
            new_payload = build_dashboard_payload(
                selected_company,
                selected_competitors,
            )
            st.session_state.dashboard_payload = new_payload
            st.session_state.dashboard_selection = selection
        except Exception as exc:
            st.session_state.dashboard_payload = {
                "status": "error",
                "message": "The analysis could not be completed.",
                "details": {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            }
            st.session_state.dashboard_selection = selection

payload = st.session_state.dashboard_payload

if not isinstance(payload, dict):
    st.error("The dashboard did not receive a valid analysis result.")
    st.stop()

if payload.get("status") != "success":
    st.error(payload.get("message", "The analysis could not be completed."))
    with st.expander("Technical details"):
        st.json(payload.get("details", {}))
    st.stop()

metrics = payload.get("metrics", {})
summary = payload.get("group_summary", {})
bridge = payload.get("growth_gap_bridge", {})

required_metrics = [
    "company_growth_percent",
    "market_growth_percent",
    "growth_gap_percentage_points",
    "share_change_percentage_points",
]

missing_metrics = [name for name in required_metrics if name not in metrics]
if missing_metrics:
    st.error(
        "The analysis is missing required metrics: "
        + ", ".join(missing_metrics)
    )
    st.stop()

groups_source = payload.get("groups", [])
groups_frame = (
    groups_source.copy()
    if isinstance(groups_source, pd.DataFrame)
    else pd.DataFrame(groups_source)
)

competitors_source = payload.get("competitors", [])
competitors_frame = (
    competitors_source.copy()
    if isinstance(competitors_source, pd.DataFrame)
    else pd.DataFrame(competitors_source)
)

st.markdown(
    f'<div class="hero">'
    f'<div class="hero-eyebrow">Commercial performance intelligence</div>'
    f'<div class="hero-title">A clearer view of {payload.get("company", selected_company)} performance</div>'
    f'<div class="hero-copy">Connect market growth, company execution, '
    f'therapeutic-group dynamics and competitor movement in one evidence-led workspace.</div>'
    f'<div class="hero-meta">COMPANY · {payload.get("company", selected_company)} '
    f'&nbsp;&nbsp;|&nbsp;&nbsp; PERIOD · {payload.get("data_period", "Period unavailable")} '
    f'&nbsp;&nbsp;|&nbsp;&nbsp;'
    f'<span class="status-pill">'
    f'{"Market totals reconciled" if metrics.get("reconciles") else "Reconciliation needs review"}'
    f'</span></div></div>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# KPI band
# ---------------------------------------------------------
kpis = st.columns(4, gap="medium")

with kpis[0]:
    st.metric(
        "Company sales growth",
        f"{fmt_number(metrics.get('company_growth_percent'))}%",
        help="Year-on-year sales value growth.",
    )

with kpis[1]:
    st.metric(
        "Total market growth",
        f"{fmt_number(metrics.get('market_growth_percent'))}%",
        help="Year-on-year growth of the total market in the company analysis dataset.",
    )

with kpis[2]:
    gap = safe_float(metrics.get("growth_gap_percentage_points"))
    st.metric(
        "Growth gap",
        f"{fmt_number(gap)} pp",
        delta=f"{fmt_number(gap)} pp vs market" if gap is not None else None,
        delta_color="inverse",
        help="Company growth minus total-market growth.",
    )

with kpis[3]:
    share_change = metrics.get("share_change_percentage_points")
    st.metric(
        "Market-share change",
        f"{fmt_number(share_change, 4)} pp",
        delta=f"{fmt_number(share_change, 4)} pp",
        delta_color="inverse",
        help="Change in market share in percentage points.",
    )

with st.expander("More performance indicators", expanded=False):
    more = st.columns(4)

    more[0].metric(
        "Sales change",
        fmt_number(metrics.get("company_sales_change")),
    )

    more[1].metric(
        "Unit growth",
        f"{fmt_number(metrics.get('unit_growth_percent'))}%",
    )

    more[2].metric(
        "Value-per-unit change",
        f"{fmt_number(metrics.get('value_per_unit_change_percent'))}%",
        help="Not proof of a price increase; mix and unit definitions can affect this measure.",
    )

    more[3].metric(
        "Market reconciliation",
        "Passed" if metrics.get("reconciles") else "Review",
        delta=(
            "Both periods match"
            if metrics.get("reconciles")
            else "Check source totals"
        ),
        delta_color="normal" if metrics.get("reconciles") else "inverse",
    )

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# Executive overview
# ---------------------------------------------------------
if page == "Executive overview":
    section_header(
        "01 / Executive brief",
        "What the numbers say",
        "A concise view of company performance relative to the market.",
    )

    left, right = st.columns([1.05, 1], gap="large")

    with left:
        st.markdown("**Company growth vs total market**")

        growth_df = pd.DataFrame(
            [
                {
                    "Entity": "Total market",
                    "Growth (%)": safe_float(
                        metrics.get("market_growth_percent"), 0
                    ),
                },
                {
                    "Entity": payload.get("company", selected_company),
                    "Growth (%)": safe_float(
                        metrics.get("company_growth_percent"), 0
                    ),
                },
            ]
        )

        fig = px.bar(
            growth_df,
            x="Entity",
            y="Growth (%)",
            color="Entity",
            text_auto=".2f",
            color_discrete_sequence=[AMBER, BRONZE_DARK],
        )
        fig.update_traces(
            textposition="outside",
            cliponaxis=False,
            marker_line_width=0,
            textfont=dict(color="#F3E8DC", size=12),
        )
        fig.update_yaxes(rangemode="tozero", title="Growth (%)")
        fig.update_xaxes(title="")

        st.plotly_chart(
            style_plot(fig, 330),
            use_container_width=True,
            config={"displayModeBar": False},
        )

        sales_gap = safe_float(metrics.get("sales_gap_vs_market_growth"))
        if sales_gap is not None:
            benchmark_text = (
                f"Sales are {fmt_number(abs(sales_gap))} source sales units "
                "below the level implied by total-market growth. This is a "
                "benchmark difference, not an estimate of recoverable sales."
            )
        else:
            benchmark_text = "The sales benchmark gap is unavailable for this selection."

        st.markdown(
            f'<div class="insight-card">'
            f'<div class="insight-title">Benchmark interpretation</div>'
            f'<div class="insight-copy">{benchmark_text}</div></div>',
            unsafe_allow_html=True,
        )

    with right:
        st.markdown("**Therapeutic-group pulse**")

        g1, g2 = st.columns(2)
        g1.metric(
            "Material groups",
            int(summary.get("material_groups_analyzed", 0)),
        )
        g2.metric(
            "Below group-market growth",
            int(summary.get("groups_growing_slower_than_market", 0)),
        )

        g3, g4 = st.columns(2)
        g3.metric(
            "Above group-market growth",
            int(summary.get("groups_growing_faster_than_market", 0)),
        )
        g4.metric(
            "Share-declining groups",
            int(summary.get("groups_with_declining_within_group_share", 0)),
        )

        st.markdown("**Growth-gap bridge**")

        bridge_df = pd.DataFrame(
            [
                {
                    "Component": "Within-group relative performance",
                    "Sales units": safe_float(
                        bridge.get("within_group_relative_performance_effect"),
                        0,
                    ),
                },
                {
                    "Component": "Group-mix benchmark effect",
                    "Sales units": safe_float(
                        bridge.get("group_mix_effect_vs_total_market"),
                        0,
                    ),
                },
            ]
        )

        fig = px.bar(
            bridge_df,
            x="Sales units",
            y="Component",
            orientation="h",
            color="Component",
            text_auto=".1f",
            color_discrete_sequence=[FOREST, AMBER],
        )
        fig.update_traces(
            textposition="outside",
            cliponaxis=False,
            marker_line_width=0,
            textfont=dict(color="#F3E8DC", size=11),
        )
        fig.update_layout(showlegend=False)

        bridge_fig = style_plot(fig, 260)
        bridge_fig.update_layout(
            margin=dict(l=250, r=70, t=20, b=35),
            yaxis=dict(automargin=True, gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID),
            xaxis=dict(automargin=True, showgrid=False, zeroline=True, zerolinecolor=GRID, linecolor=GRID),
        )

        st.plotly_chart(
            bridge_fig,
            use_container_width=True,
            config={"displayModeBar": False},
        )
        st.caption("Arithmetic benchmark decomposition; not causal attribution.")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    section_header(
        "02 / Recommended focus",
        "Where to investigate first",
        "Prioritize material gaps, then validate the story with brand- or product-level evidence.",
    )

    if (
        not groups_frame.empty
        and "sales_vs_group_market_growth_benchmark" in groups_frame.columns
    ):
        worst = groups_frame.sort_values(
            "sales_vs_group_market_growth_benchmark",
            ascending=True,
            na_position="last",
        ).head(3)

        cards = st.columns(3, gap="medium")

        for idx, (_, row) in enumerate(worst.iterrows()):
            with cards[idx]:
                st.markdown(
                    f'<div class="insight-card" style="height:100%">'
                    f'<div class="section-kicker">Priority {idx + 1}</div>'
                    f'<div class="insight-title">{row.get("group", "Therapeutic group")}</div>'
                    f'<div class="insight-copy">Sales gap vs group-market benchmark: '
                    f'<b>{fmt_number(row.get("sales_vs_group_market_growth_benchmark"))}</b> source units.<br>'
                    f'Company growth: {fmt_number(row.get("company_growth_percent"))}% · '
                    f'Group-market growth: {fmt_number(row.get("market_group_growth_percent"))}%'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("Therapeutic-group benchmark data is not available for this company.")


# ---------------------------------------------------------
# Therapeutic-group analysis
# ---------------------------------------------------------
elif page == "Therapeutic groups":
    section_header(
        "03 / Portfolio dynamics",
        "Therapeutic-group performance",
        "Compare company growth with each corresponding group's market growth and rank the largest sales gaps.",
    )

    groups = groups_frame.copy()

    if groups.empty:
        st.info("No therapeutic-group data is available for this company.")
    else:
        controls = st.columns([1.2, 1, 1])

        with controls[0]:
            view = st.selectbox(
                "Show groups",
                [
                    "Largest negative sales gaps",
                    "Largest positive sales gaps",
                    "All material groups",
                ],
            )

        with controls[1]:
            min_sales = st.number_input(
                "Minimum 2025 sales",
                min_value=0.0,
                value=0.0,
                step=10.0,
            )

        with controls[2]:
            max_rows = st.selectbox(
                "Rows to display",
                [10, 20, 50, 100, "All"],
                index=1,
            )

        if "company_sales_2025" in groups.columns:
            groups = groups[
                pd.to_numeric(
                    groups["company_sales_2025"], errors="coerce"
                ).fillna(0)
                >= min_sales
            ]

        gap_col = "sales_vs_group_market_growth_benchmark"

        if gap_col not in groups.columns:
            st.warning("Sales benchmark gaps are unavailable in this dataset.")
            st.stop()

        if view == "Largest negative sales gaps":
            groups = groups[
                groups[gap_col] < 0
            ].sort_values(gap_col, ascending=True)

        elif view == "Largest positive sales gaps":
            groups = groups[
                groups[gap_col] > 0
            ].sort_values(gap_col, ascending=False)

        else:
            groups = groups.sort_values(
                gap_col,
                ascending=True,
                na_position="last",
            )

        if max_rows != "All":
            groups = groups.head(int(max_rows))

        plot_groups = groups.head(12).sort_values(
            gap_col,
            ascending=True,
        )

        if not plot_groups.empty:
            fig = px.bar(
                plot_groups,
                x=gap_col,
                y="group",
                orientation="h",
                color=gap_col,
                color_continuous_scale=[CORAL, AMBER, FOREST],
                text_auto=".1f",
                labels={
                    gap_col: "Sales gap vs group benchmark",
                    "group": "Therapeutic group",
                },
            )
            fig.update_traces(
                textposition="outside",
                cliponaxis=False,
                marker_line_width=0,
            )
            fig.update_layout(coloraxis_showscale=False)

            st.plotly_chart(
                style_plot(fig, max(360, 31 * len(plot_groups))),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        else:
            st.info("No groups match the selected filters.")

        display_names = {
            "group": "Therapeutic group",
            "company_sales_2025": "Company sales · 2025",
            "company_growth_percent": "Company growth (%)",
            "market_group_growth_percent": "Group-market growth (%)",
            "growth_gap_percentage_points": "Growth gap (pp)",
            "sales_vs_group_market_growth_benchmark": "Sales gap vs group benchmark",
            "within_group_share_change_percentage_points": "Within-group share change (pp)",
            "classification": "Performance classification",
        }

        display_cols = [
            column for column in display_names if column in groups.columns
        ]
        display_df = groups[display_cols].rename(
            columns=display_names
        ).copy()

        numeric_cols = display_df.select_dtypes(include="number").columns
        display_df[numeric_cols] = display_df[numeric_cols].round(2)

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=420,
        )

        st.download_button(
            "⬇ Download filtered group analysis",
            data=display_df.to_csv(index=False).encode("utf-8"),
            file_name=(
                f"{payload.get('company', selected_company).replace('*', 'star')}"
                "_therapeutic_groups.csv"
            ),
            mime="text/csv",
        )

        st.caption(
            "A negative sales gap means observed company sales are below the "
            "level implied by that group's market growth. It does not establish why."
        )


# ---------------------------------------------------------
# Competitor intelligence
# ---------------------------------------------------------
elif page == "Competitor intelligence":
    section_header(
        "04 / Competitive landscape",
        "Growth and share movement",
        "Compare the selected companies on sales growth, market-share movement and scale.",
    )

    comp = competitors_frame.copy()

    if comp.empty:
        st.info(
            "Choose competitors from the sidebar to populate the comparison."
        )
    else:
        display_names = {
            "company": "Company",
            "sales_2025": "Sales · 2025",
            "growth_percent": "Sales growth (%)",
            "market_share_2025_percent": "Market share · 2025 (%)",
            "share_change_percentage_points": "Share change (pp)",
            "competitive_category": "Performance category",
            "weighted_score": "Weighted score",
            "market_rank": "Market rank",
        }

        display_cols = [
            column for column in display_names if column in comp.columns
        ]
        display_df = comp[display_cols].rename(
            columns=display_names
        ).copy()

        numeric_cols = display_df.select_dtypes(include="number").columns
        display_df[numeric_cols] = display_df[numeric_cols].round(2)

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )

        if {
            "company",
            "growth_percent",
            "share_change_percentage_points",
        }.issubset(comp.columns):
            fig = px.scatter(
                comp,
                x="growth_percent",
                y="share_change_percentage_points",
                text="company",
                size="sales_2025" if "sales_2025" in comp.columns else None,
                color="company",
                color_discrete_sequence=[AMBER, BRONZE_DARK, CORAL, "#B8A07A"],
                hover_data=[
                    column
                    for column in [
                        "competitive_category",
                        "market_rank",
                        "market_share_2025_percent",
                    ]
                    if column in comp.columns
                ],
            )

            fig.add_hline(
                y=0,
                line_dash="dash",
                line_color=MUTED,
                opacity=0.65,
            )
            fig.add_vline(
                x=safe_float(metrics.get("market_growth_percent"), 0),
                line_dash="dash",
                line_color=AMBER,
                opacity=0.8,
                annotation_text="Total market growth",
                annotation_position="top",
            )
            fig.update_traces(
                textposition="top center",
                marker=dict(line=dict(width=1, color="#5A4537")),
            )
            fig.update_layout(
                showlegend=False,
                xaxis_title="Sales growth (%)",
                yaxis_title="Market-share change (pp)",
            )

            st.plotly_chart(
                style_plot(fig, 420),
                use_container_width=True,
                config={"displayModeBar": False},
            )

        st.caption(
            "The scatter plot shows association between growth and share movement, not causal drivers."
        )


# ---------------------------------------------------------
# Investigation chat
# ---------------------------------------------------------
elif page == "Investigation chat":
    section_header(
        "05 / Commercial investigation assistant",
        "Ask the evidence, not just the dashboard",
        (
            "Ask follow-up questions about market growth, therapeutic groups, "
            "competitors and commercial priorities. Answers use the existing "
            "analytical agents and selected company context."
        ),
    )

    st.markdown(
        '<div class="insight-card"><div class="insight-title">Current analysis context</div>'
        f'<div class="insight-copy">Company: <b>{selected_company}</b> · '
        f'Competitors: <b>{", ".join(selected_competitors) if selected_competitors else "None selected"}</b> · '
        f'Period: <b>{payload.get("data_period", "Unavailable")}</b></div></div>',
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------
    # Chat helpers
    # -----------------------------------------------------
    import json

    def get_nested_dict(data, *keys):
        """Safely retrieve a nested dictionary."""
        current = data
        for key in keys:
            if not isinstance(current, dict):
                return {}
            current = current.get(key)
        return current if isinstance(current, dict) else {}

    def parse_json_string(value):
        """Parse JSON-formatted strings without breaking ordinary text."""
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        if not cleaned or cleaned[0] not in ("{", "["):
            return value
        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, TypeError):
            return value

    def get_readable_text(value):
        """Extract readable text from strings, lists, or narrative dictionaries."""
        value = parse_json_string(value)
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        if isinstance(value, list):
            items = []
            for item in value:
                text_value = get_readable_text(item)
                if text_value:
                    items.append(f"- {text_value}")
            return "\n".join(items) if items else None
        if isinstance(value, dict):
            for key in (
                "final_answer", "answer", "narrative", "coordinated_answer",
                "coordinated_summary", "summary", "message", "response",
                "diagnosis", "interpretation",
            ):
                text_value = get_readable_text(value.get(key))
                if text_value:
                    return text_value
        return None

    def format_structured_evidence(data, company_name, period):
        """Render known commercial evidence fields as readable Markdown."""
        if not isinstance(data, dict):
            return None
        sections = [f"### Commercial diagnosis: {company_name}"]
        if period:
            sections.append(f"**Period:** {period}")
        fields = (
            ("fastest_growing_therapeutic_groups", "Fastest-growing therapeutic groups"),
            ("growth_drivers", "Growth drivers"),
            ("declining_groups", "Declining therapeutic groups"),
            ("ranking_notes", "Ranking notes"),
            ("verified_facts", "What the data shows"),
            ("interpretations_and_hypotheses", "Interpretations to investigate"),
            ("priority_investigations", "Recommended next investigations"),
            ("limitations", "Limitations"),
            ("data_source", "Data source"),
            ("data_sources", "Data sources"),
        )
        for key, label in fields:
            value = data.get(key)
            if value is None or value == "" or value == [] or value == {}:
                continue
            readable = get_readable_text(value)
            if readable:
                sections.append(f"**{label}**\n{readable}")
        return "\n\n".join(sections) if len(sections) > 1 else None

    def extract_agent_answer(response):
        """Extract readable agent output and retain details for the evidence expander."""
        normalized = parse_json_string(response)
        response_details = normalized if isinstance(normalized, dict) else {"raw_response": response}

        execution = get_nested_dict(response_details, "execution")
        result = parse_json_string(execution.get("result"))
        if not isinstance(result, dict):
            result = parse_json_string(response_details.get("result"))
        if not isinstance(result, dict):
            result = {}

        coordinated_summary = (
            get_nested_dict(result, "coordinated_summary")
            or get_nested_dict(execution, "coordinated_summary")
            or get_nested_dict(response_details, "coordinated_summary")
        )

        details = {
            "execution": execution,
            "result": result,
            "coordinated_summary": coordinated_summary,
            "response": response_details,
        }

        candidates = [coordinated_summary, result, execution, response_details]
        narrative_keys = (
            "final_answer", "answer", "narrative", "coordinated_answer",
            "summary", "message", "response", "diagnosis",
        )
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            for key in narrative_keys:
                readable = get_readable_text(candidate.get(key))
                if not readable:
                    continue
                company_name = (
                    candidate.get("company")
                    or response_details.get("company")
                    or selected_company
                )
                period = (
                    candidate.get("data_period")
                    or candidate.get("period")
                    or response_details.get("data_period")
                    or payload.get("data_period")
                )
                heading = f"### Commercial diagnosis: {company_name}"
                if period:
                    heading += f"\n\n**Period:** {period}"
                return f"{heading}\n\n{readable}", details

        company_name = (
            coordinated_summary.get("company")
            or result.get("company")
            or response_details.get("company")
            or selected_company
        )
        period = (
            coordinated_summary.get("data_period")
            or coordinated_summary.get("period")
            or result.get("data_period")
            or response_details.get("data_period")
            or payload.get("data_period")
        )

        for source in (coordinated_summary, result, execution, response_details):
            structured_answer = format_structured_evidence(source, company_name, period)
            if structured_answer:
                return structured_answer, details

        status = execution.get("status", response_details.get("status", "unknown"))
        if status not in {"success", "partial_success"}:
            error_message = (
                execution.get("message")
                or response_details.get("message")
                or response_details.get("error")
                or "I couldn't complete that analysis. Try asking a more specific question."
            )
            missing_inputs = execution.get("missing_inputs") or response_details.get("missing_inputs") or []
            if missing_inputs:
                error_message += "\n\n**Missing inputs:** " + ", ".join(map(str, missing_inputs))
            return error_message, details

        try:
            from app.agents.agent import format_result
            formatted = get_readable_text(format_result(response_details))
            if formatted:
                return formatted, details
        except Exception:
            pass

        return (
            "The analysis completed, but the agent did not return a readable narrative "
            "or recognized evidence fields. Open **Supporting evidence and execution "
            "details** below to inspect the response structure.",
            details,
        )

    # -----------------------------------------------------
    # Initialize chat history
    # -----------------------------------------------------
    if "commercial_chat_history" not in st.session_state:
        st.session_state.commercial_chat_history = []

    suggested_questions = [
        "Why is this company growing slower than the market?",
    ]

    st.markdown("**Start an investigation**")
    suggestion_cols = st.columns(2, gap="small")

    for idx, suggested in enumerate(suggested_questions):
        with suggestion_cols[idx % 2]:
            if st.button(
                suggested,
                key=f"chat_suggestion_{idx}",
                use_container_width=True,
            ):
                st.session_state.pending_commercial_question = suggested

    # -----------------------------------------------------
    # Display previous messages
    # -----------------------------------------------------
    for message in st.session_state.commercial_chat_history:
        with st.chat_message(
            message["role"],
            avatar="🧬" if message["role"] == "assistant" else "👤",
        ):
            st.markdown(message["content"])

            if message.get("evidence"):
                with st.expander("Supporting evidence and execution details"):
                    st.json(message["evidence"])

    # -----------------------------------------------------
    # Accept user question
    # -----------------------------------------------------
    pending = st.session_state.pop(
        "pending_commercial_question",
        None,
    )

    typed_question = st.chat_input(
        "Ask a commercial question…"
    )

    question = typed_question or pending

    if question:
        st.session_state.commercial_chat_history.append(
            {
                "role": "user",
                "content": question,
            }
        )

        with st.chat_message("user", avatar="👤"):
            st.markdown(question)

        with st.chat_message("assistant", avatar="🧬"):
            with st.spinner(
                "Coordinating the relevant commercial analyses..."
            ):
                try:
                    # Pass selected company and competitor context
                    # to the existing commercial agent.
                    response = run_agent(
                        question,
                        tool_inputs={
                            "company": selected_company,
                            "competitors": selected_competitors,
                        },
                    )

                    # Extract readable answer and retain diagnostic details.
                    answer, response_details = extract_agent_answer(response)

                    execution = response_details.get("execution", {})
                    result = response_details.get("result", {})
                    coordinated_summary = response_details.get(
                        "coordinated_summary",
                        {},
                    )

                    status = (
                        execution.get("status", "unknown")
                        if isinstance(execution, dict)
                        else "unknown"
                    )

                    # Display only the readable answer in the chat.
                    st.markdown(answer)

                    # Keep technical response details in the expander.
                    evidence = {
                        "action": (
                            response.get("plan", {}).get("action")
                            if isinstance(response, dict)
                            and isinstance(response.get("plan"), dict)
                            else None
                        ),
                        "status": status,
                        "data_sources": (
                            result.get(
                                "data_sources",
                                result.get("data_source"),
                            )
                            if isinstance(result, dict)
                            else None
                        ),
                        "specialists": (
                            result.get("specialist_analysis", {}).get(
                                "successful_agents"
                            )
                            if isinstance(result, dict)
                            and isinstance(
                                result.get("specialist_analysis"),
                                dict,
                            )
                            else None
                        ),
                        "response_keys": (
                            list(response.keys())
                            if isinstance(response, dict)
                            else str(type(response))
                        ),
                        "execution_keys": (
                            list(execution.keys())
                            if isinstance(execution, dict)
                            else str(type(execution))
                        ),
                        "result_keys": (
                            list(result.keys())
                            if isinstance(result, dict)
                            else str(type(result))
                        ),
                        "coordinated_summary_keys": (
                            list(coordinated_summary.keys())
                            if isinstance(coordinated_summary, dict)
                            else str(type(coordinated_summary))
                        ),
                    }

                    st.session_state.commercial_chat_history.append(
                        {
                            "role": "assistant",
                            "content": answer,
                            "evidence": evidence,
                        }
                    )

                except Exception as exc:
                    answer = (
                        "I couldn't complete that analysis "
                        f"({type(exc).__name__}: {exc}). "
                        "Please check the terminal for details and try again."
                    )

                    st.error(answer)

                    st.session_state.commercial_chat_history.append(
                        {
                            "role": "assistant",
                            "content": answer,
                        }
                    )

    # -----------------------------------------------------
    # Clear conversation
    # -----------------------------------------------------
    clear_col, hint_col = st.columns([1, 4])

    with clear_col:
        if st.button(
            "Clear conversation",
            key="clear_commercial_chat",
        ):
            st.session_state.commercial_chat_history = []
            st.rerun()

    with hint_col:
        st.caption(
            "Answers are generated from the existing analytical tools. "
            "Aggregate data can identify signals to investigate, but does "
            "not establish causation by itself."
        )
# ---------------------------------------------------------
# Evidence and methodology
# ---------------------------------------------------------
else:
    section_header(
        "06 / Trust & traceability",
        "Evidence, hypotheses and methodology",
        "Keep what is measured separate from what still needs investigation.",
    )

    facts_col, hypotheses_col = st.columns(2, gap="large")

    with facts_col:
        st.markdown("**Verified facts**")

        for fact in payload.get("verified_facts", []):
            st.markdown(f"- {fact}")

    with hypotheses_col:
        st.markdown("**Interpretations to investigate**")

        for hypothesis in payload.get("hypotheses", []):
            st.markdown(f"- {hypothesis}")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    section_header("Investigation plan", "Recommended next checks")

    for index, item in enumerate(
        payload.get("investigations", []),
        start=1,
    ):
        st.markdown(
            f'<div class="insight-card">'
            f'<div class="insight-title">{index:02d} &nbsp; Investigation priority</div>'
            f'<div class="insight-copy">{item}</div></div>',
            unsafe_allow_html=True,
        )

    left, right = st.columns(2, gap="large")

    with left:
        st.markdown("**Limitations**")

        for limitation in payload.get("limitations", []):
            st.markdown(f"- {limitation}")

    with right:
        st.markdown("**Data sources**")

        for source in payload.get("sources", []):
            st.markdown(f"- `{source}`")

        specialists = payload.get("specialists", [])
        st.markdown(
            f"**Specialists reporting success:** {', '.join(specialists)}"
        )


# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------
st.markdown(
    "<div style='height:18px'></div><hr>",
    unsafe_allow_html=True,
)

footer_left, footer_right = st.columns([2, 1])

with footer_left:
    st.markdown(
        "<div class='muted-note'>PHARMA COMMERCIAL INTELLIGENCE AI · "
        "Evidence-led analysis for investigation and decision support.</div>",
        unsafe_allow_html=True,
    )

with footer_right:
    st.markdown(
        "<div class='muted-note' style='text-align:right'>"
        "IMS MAT SEP 2025 / SEP 2024</div>",
        unsafe_allow_html=True,
    )

