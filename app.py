"""PriorityLens - customer feedback triage console (Streamlit).
Upload an Excel/CSV of feedback, or use the sample file.
Run with:  python -m streamlit run app.py"""
import os

import pandas as pd
import plotly.express as px
import streamlit as st

from generator import SAMPLE_EXCEL, generate
from pipeline import build_backlog, load_feedback_file, process_feedback

st.set_page_config(page_title="PriorityLens", page_icon="◐", layout="wide")

# ---------- Look & feel: soft grey page, rounded cards, mono status pills ----------
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {font-family: 'DM Sans', sans-serif;}
[data-testid="stHeader"] {background: transparent;}
#MainMenu, footer {visibility: hidden;}
.block-container {max-width: 1100px; background: #f3f3f1; border-radius: 44px; border: 1px solid #ecece9;
  padding: 2.5rem 3.5rem 2rem 3.5rem !important; margin: 1.5rem auto;}
.topbar {display: flex; justify-content: space-between; align-items: center; padding-bottom: 1rem;
  border-bottom: 1px solid #e2e2df; margin-bottom: 1rem;}
.brand {font-size: 1.4rem; font-weight: 700; color: #1f1f1f;}
.mono {font-family: 'JetBrains Mono', ui-monospace, Consolas, monospace; font-size: 0.72rem; color: #6f6f6b;}
.pill {display: inline-block; background: #fff; border-radius: 999px; padding: 5px 14px; font-size: 0.75rem;
  box-shadow: 0 1px 6px rgba(0,0,0,0.07); margin: 0 6px 6px 0;}
.h2 {font-size: 1.15rem; font-weight: 700; color: #1f1f1f; margin: 2.2rem 0 0.8rem 0;}
.card {background: #fff; border: 1px solid #ecece9; border-radius: 28px; padding: 1.5rem 1rem; text-align: center;}
.card-label {font-size: 0.8rem; color: #8a8a86;}
.card-value {font-size: 1.6rem; font-weight: 700; color: #1f1f1f; margin-top: 0.4rem; line-height: 1.2;}
[data-testid="stVerticalBlockBorderWrapper"] {background: #fff; border-radius: 28px; border: 1px solid #ecece9;}
[data-testid="stDataFrame"] {border-radius: 20px; overflow: hidden;}
[data-testid="stAlert"] {border-radius: 20px;}
[data-testid="stSidebar"] {background: #ecece9;}
.stDownloadButton button {border-radius: 999px; background: #1f1f1f; color: #fff; border: none;}
.footer {border-top: 1px solid #e2e2df; margin-top: 2.5rem; padding-top: 1rem;}
</style>""", unsafe_allow_html=True)


def pill(text, mono=True):
    return f'<span class="pill {"mono" if mono else ""}">{text}</span>'


def section(number, title):
    st.markdown(f'<div class="h2">{pill(number)} {title}</div>', unsafe_allow_html=True)


def card(label, value):
    return f'<div class="card"><div class="card-label">{label}</div><div class="card-value">{value}</div></div>'


# ---------- 1. Load feedback: your own Excel/CSV file, or the sample ----------
if not os.path.exists(SAMPLE_EXCEL):
    generate()

st.sidebar.header("Input")
uploaded = st.sidebar.file_uploader("Upload an Excel (.xlsx) or CSV file", type=["xlsx", "csv"])
with open(SAMPLE_EXCEL, "rb") as f:
    st.sidebar.download_button("Download sample Excel template", f.read(), "sample_feedback.xlsx")

if uploaded is not None:
    raw, source_name = load_feedback_file(uploaded), uploaded.name
else:
    raw, source_name = pd.read_excel(SAMPLE_EXCEL), os.path.basename(SAMPLE_EXCEL) + " (sample)"

try:
    df = process_feedback(raw)
except ValueError as error:
    st.error(str(error))
    st.stop()

# ---------- 2. Filters ----------
st.sidebar.header("Filters")
categories = st.sidebar.multiselect("Category", sorted(df["category"].unique()), default=sorted(df["category"].unique()))
sources = st.sidebar.multiselect("Source", sorted(df["source"].unique()), default=sorted(df["source"].unique()))
sentiments = st.sidebar.multiselect("Sentiment", sorted(df["sentiment"].unique()), default=sorted(df["sentiment"].unique()))

cleaned_rows = len(df)
view = df[df["category"].isin(categories) & df["source"].isin(sources) & df["sentiment"].isin(sentiments)]

# ---------- Header + pipeline status ----------
st.markdown(f'<div class="topbar"><div class="brand">PriorityLens {pill("v1.0")}</div>'
            f'<div class="mono">source: {source_name}</div></div>', unsafe_allow_html=True)
st.markdown(pill(f"rows loaded: {len(raw)}") + pill(f"after cleaning: {cleaned_rows}")
            + pill(f"dropped: {len(raw) - cleaned_rows}") + pill(f"in view: {len(view)}")
            + pill("labelling: keyword rules"), unsafe_allow_html=True)

if view.empty:
    st.warning("No feedback matches these filters.")
    st.stop()
backlog = build_backlog(view)

# ---------- Metric cards ----------
share = view["sentiment"].value_counts(normalize=True) * 100
mix = f"{share.get('Positive', 0):.0f}% / {share.get('Neutral', 0):.0f}% / {share.get('Negative', 0):.0f}%"
col1, col2, col3 = st.columns(3)
col1.markdown(card("Feedback processed", len(view)), unsafe_allow_html=True)
col2.markdown(card("Sentiment (Pos / Neu / Neg)", mix), unsafe_allow_html=True)
col3.markdown(card("Top priority", backlog.iloc[0]["backlog_item"]), unsafe_allow_html=True)

# ---------- Chart ----------
section("01", "Feedback volume by category")
colors = {"Positive": "#d0d0cb", "Neutral": "#9a9a96", "Negative": "#222222"}
chart = px.histogram(view, x="category", color="sentiment", color_discrete_map=colors)
chart.update_layout(xaxis_title=None, yaxis_title="Feedback items", legend_title=None, bargap=0.35,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font_family="DM Sans", margin=dict(t=20, b=10), legend=dict(orientation="h", y=1.12))
chart.update_yaxes(gridcolor="#e8e8e5")
with st.container(border=True):
    st.plotly_chart(chart)

# ---------- Ranked table ----------
section("02", "Priority backlog: bugs & feature requests, ranked by RICE")
table = backlog[backlog["category"].isin(["Bug", "Feature Request"])].reset_index(drop=True)
table["rank"] = table.index + 1
with st.container(border=True):
    st.dataframe(table, hide_index=True)
st.caption("RICE Score = (Reach x Impact x Confidence) / Effort")

# ---------- Raw data ----------
with st.expander("Individual feedback records"):
    st.dataframe(view[["feedback_id", "source", "raw_feedback_text", "category", "sentiment", "theme"]], hide_index=True)

st.markdown('<div class="footer mono">PriorityLens v1.0 &nbsp;·&nbsp; pipeline: clean → label → RICE</div>',
            unsafe_allow_html=True)
