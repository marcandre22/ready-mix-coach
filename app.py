# app.py

import streamlit as st
import pandas as pd
from openai import OpenAI
from datetime import datetime

from kb.knowledge import BEST_PRACTICE
from prompts.instructions import build_prompt
from style.tone_style import apply_cdware_style

# --------------------------
# CONFIG & STYLE
# --------------------------
st.set_page_config(page_title="CDWARE Ready‑Mix Coach", layout="wide", initial_sidebar_state="expanded")
apply_cdware_style()
st.image("cdware_logo.png", width=260)
st.title("CDWARE Ready‑Mix Coach")

# --------------------------
# LOAD DATA
# --------------------------
@st.cache_data
def load_data():
    return pd.read_csv("data/example_input.csv")

raw_df = load_data()

# --------------------------
# SIDEBAR
# --------------------------
st.sidebar.header("Dataset Tools")
if st.sidebar.checkbox("Show raw table"):
    st.dataframe(raw_df.head(30), use_container_width=True)

if st.sidebar.button("Export CSV"):
    st.sidebar.download_button("Download CSV", raw_df.to_csv(index=False), "ready_mix.csv")

# --------------------------
# USER PROMPT
# --------------------------
q = st.text_input("Ask the coach:")
if q:
    with st.spinner("Thinking..."):
        client = OpenAI()
        out = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": build_prompt(q, raw_df, BEST_PRACTICE)
                }
            ]
        )
        st.markdown(out.choices[0].message.content)

# --------------------------
# KPI Button (optional)
# --------------------------
if st.button("📈 Show KPI Charts"):
    st.subheader("Cycle Duration Breakdown")
    stage_cols = [col for col in raw_df.columns if col.startswith("dur_")]
    st.bar_chart(raw_df[stage_cols].mean())
