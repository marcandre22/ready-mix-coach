# Ready‑Mix Coach – CDWARE (v3.12)
# English‑only. Adds follow-up memory support for smarter coaching. Modularized with knowledge, tone, and instructions.

import streamlit as st
import pandas as pd
from openai import OpenAI
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
# 1. Load data
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
# 2. Prompt builder with follow-up memory
# -------------------------------------------------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

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

Best practices:
{BEST_PRACTICE}

Tone:
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
