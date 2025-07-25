# app.py – Ready-Mix Coach (Modular)

import streamlit as st
import pandas as pd
from openai import OpenAI
from knowledge import BEST_PRACTICE
from tone_style import COACH_STYLE
from instruction_set import GUIDELINES
from dummy_data_gen import load_data

st.set_page_config(page_title="Ready‑Mix Coach", layout="wide", initial_sidebar_state="expanded")

# --- Logo and Title ---
st.image("cdware_logo.png", width=260)
st.title("CDWARE Ready‑Mix Coach")

# --- Load data ---
raw_df = load_data()

# --- Sidebar ---
st.sidebar.header("Dataset")
if st.sidebar.checkbox("Show raw table"):
    st.dataframe(raw_df.head(30), use_container_width=True)
if st.sidebar.button("Export CSV"):
    st.sidebar.download_button("Download CSV", raw_df.to_csv(index=False), "ready_mix.csv")

# --- Prompt Builder ---
def build_prompt(q: str) -> str:
    kpis = {
        "avg_cycle": f"{raw_df['cycle_time'].mean():.1f} min",
        "avg_wait": f"{raw_df['dur_waiting'].mean():.1f} min",
        "avg_load": f"{raw_df['dur_loaded'].mean():.1f} min",
        "avg_water": f"{raw_df['water_added_L'].mean():.1f} L",
        "avg_rpm":   f"{raw_df['drum_rpm'].mean():.1f} rpm"
    }
    snap = "\n".join([f"- {k.replace('_',' ').title()}: {v}" for k, v in kpis.items()])

    water_by_driver = raw_df.groupby("driver")["water_added_L"].sum().sort_values(ascending=False)
    driver_lines = "\n".join([f"  • {d}: {w:.1f} L" for d, w in water_by_driver.head(5).items()])

    return f"""
You are a ready‑mix fleet optimization coach.
Use the context below to answer the question precisely and constructively.

Snapshot KPIs (based on {len(raw_df)} jobs):
{snap}

Top drivers by water added:
{driver_lines}

Best practices:
{BEST_PRACTICE}

Coaching tone:
{COACH_STYLE}

Instructions:
{GUIDELINES}

Question: {q}
"""

# --- Chat ---
q = st.text_input("Ask the coach:")
if q:
    with st.spinner("Thinking…"):
        client = OpenAI()
        out = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": build_prompt(q)}]
        )
        st.markdown(out.choices[0].message.content)

# --- KPI Button ---
if st.button("📈 KPI Charts"):
    st.subheader("Average stage durations (min)")
    st.bar_chart(raw_df.filter(like="dur_").mean())
