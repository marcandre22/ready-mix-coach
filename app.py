# Ready‑Mix Coach – CDWARE (v3.12)
# Adds benchmark input fields and adaptive insights

import streamlit as st
import pandas as pd
import random
from openai import OpenAI
from datetime import datetime, timedelta
from io import BytesIO

from knowledge import BEST_PRACTICE
from tone_style import COACH_STYLE
from instruction_set import GUIDELINES
from dummy_data_gen import load_data

st.set_page_config(page_title="Ready‑Mix Coach", layout="wide", initial_sidebar_state="expanded")

# --- Dark‑mode styling ---
st.markdown(
    """<style>
    body { background:#121212; color:#f1f1f1; }
    .main { background:#121212; }
    h1,h2,h3 { color:#E7662E; }
    .stButton>button { background:#E7662E; color:white; font-weight:bold; }
    </style>""",
    unsafe_allow_html=True,
)

st.image("cdware_logo.png", width=260)
st.title("CDWARE Ready‑Mix Coach")

# -------------------------------------------------------------------
# 1. Generate simulated telematics / ERP data
# -------------------------------------------------------------------
raw_df = load_data()

# -------------------------------------------------------------------
# Sidebar utilities
# -------------------------------------------------------------------
st.sidebar.header("Dataset")
if st.sidebar.checkbox("Show raw table"):
    st.dataframe(raw_df.head(30), use_container_width=True)
if st.sidebar.button("Export CSV"):
    st.sidebar.download_button("Download CSV", raw_df.to_csv(index=False), "ready_mix.csv")

# -------------------------------------------------------------------
# 2. Prompt builder with memory and benchmark inputs
# -------------------------------------------------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

col1, col2, col3 = st.columns(3)
col4, col5, col6 = st.columns(3)

benchmark_util = col1.number_input("Benchmark Utilization (%)", value=85.0)
benchmark_m3hr = col2.number_input("Benchmark m³/HR", value=3.5)
benchmark_m3load = col3.number_input("Benchmark m³/Load", value=7.6)
benchmark_wait = col4.number_input("Benchmark Wait Time (min)", value=19.0)
benchmark_ot = col5.number_input("Benchmark OT (%)", value=10.0)
benchmark_fuel = col6.number_input("Fuel cost $/L", value=1.75)

benchmarks = f"""
Benchmarks (user-defined):
- Utilization: {benchmark_util:.1f}%
- m³/HR: {benchmark_m3hr:.2f}
- m³/Load: {benchmark_m3load:.2f}
- Wait Time: {benchmark_wait:.1f} min
- OT: {benchmark_ot:.1f}%
- Fuel cost: ${benchmark_fuel:.2f}/L
"""

def build_prompt_with_memory(question):
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

    memory = "\n".join([f"User: {q['user']}\nCoach: {q['coach']}" for q in st.session_state.chat_history])

    return f"""You are an expert ready‑mix dispatch coach. NEVER quote the knowledge directly.

Session history:
{memory}

Snapshot KPIs:
Jobs: {len(raw_df)}
{snap}

Top drivers by water:
{driver_lines}

{benchmarks}

Best practices:
{BEST_PRACTICE}

Coaching tone:
{COACH_STYLE}

Instructions:
{GUIDELINES}

Current question: {question}
"""

# -------------------------------------------------------------------
# 3. Chat interface with memory
# -------------------------------------------------------------------
question = st.text_input("Ask the coach:")
if question:
    with st.spinner("Thinking…"):
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":build_prompt_with_memory(question)}]
        )
        answer = response.choices[0].message.content
        st.markdown(answer)
        st.session_state.chat_history.append({"user": question, "coach": answer})

# -------------------------------------------------------------------
# 4. Quick insights button
# -------------------------------------------------------------------
if st.button("📈 KPI Charts"):
    st.subheader("Average stage durations (min)")
    st.bar_chart(raw_df.filter(like="dur_").mean())
