# Ready‑Mix Coach – CDWARE (v3.8)
# English‑only. Coach leverages internal best‑practice principles (crafted from industry literature).

import streamlit as st
import pandas as pd
import random
from openai import OpenAI
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="Ready‑Mix Coach", layout="wide", initial_sidebar_state="expanded")

# -------------------------------------------------------------------
# Brand Styling (dark mode)
# -------------------------------------------------------------------
st.markdown(
    """
    <style>
        body { background-color:#121212; color:#f1f1f1; }
        .main { background-color:#121212; }
        h1, h2, h3 { color:#E7662E; }
        .stButton button { background-color:#E7662E; color:white; font-weight:bold; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.image("cdware_logo.png", width=280)
st.title("CDWARE Ready‑Mix Coach")

# -------------------------------------------------------------------
# 0. Embedded Best‑Practice Cheat‑Sheet (derived from trusted industry guides)
# -------------------------------------------------------------------
BEST_PRACTICE_NOTES = """
Key ready‑mix dispatch practices:
• Plan each pour in detail; confirm mix, volume, and site readiness ahead of truck loading.
• Keep average loading dwell ≤ 7 min to avoid plant congestion.
• Provide automatic ETA updates to the site at 50 % and 90 % of travel.
• Escalate if on‑site waiting exceeds 10 min — aim for trucks to be ready to discharge immediately.
• Track water additions and drum RPM to maintain quality on the road (RPM ≥ 4).
• Close the loop post‑wash: update KPIs the same day to inform morning stand‑up.
"""

# -------------------------------------------------------------------
# 1. Load Simulated Telematics Data
# -------------------------------------------------------------------
@st.cache_data

def load_data():
    drivers = ["Marc", "Julie", "Antoine", "Sarah", "Luc", "Melanie", "Simon", "Elise"]
    stages  = ["dispatch", "loaded", "en_route", "waiting", "discharging", "washing", "back"]
    plants  = ["Montreal", "Laval", "Quebec", "Drummondville"]
    sites   = ["Longueuil", "Trois‑Rivieres", "Sherbrooke", "Repentigny"]
    rows = []
    for i in range(28):
        durs = [random.randint(10,25), random.randint(5,10), random.randint(15,30),
                random.randint(5,20), random.randint(10,20), random.randint(5,10), random.randint(10,25)]
        row = {
            "job_id": f"J{1000+i}",
            "driver": random.choice(drivers),
            "origin_plant": random.choice(plants),
            "job_site": random.choice(sites),
            "cycle_time": sum(durs)
        }
        for s,v in zip(stages,durs):
            row[f"dur_{s}"] = v
        rows.append(row)
    return pd.DataFrame(rows)

raw_df = load_data()

# -------------------------------------------------------------------
# Sidebar – Data & Export
# -------------------------------------------------------------------
st.sidebar.header("Data & Export")
if st.sidebar.checkbox("Show raw data"):
    st.dataframe(raw_df, use_container_width=True)

if st.sidebar.button("Export CSV"):
    st.sidebar.download_button("Download", raw_df.to_csv(index=False), "ready_mix.csv")

# -------------------------------------------------------------------
# 2. Prompt Builder with data + best practices
# -------------------------------------------------------------------

def build_prompt(question: str) -> str:
    stage_avgs = raw_df.filter(like="dur_").mean()
    snapshot  = "\n".join([f"- Avg {c.replace('dur_','').capitalize()}: {v:.1f} min" for c,v in stage_avgs.items()])
    prompt = f"""
You are a ready‑mix dispatch coach.
Leverage both the live telematics summary and the internal best‑practice notes below to answer.

---
Fleet snapshot
Jobs: {len(raw_df)} | Avg total cycle: {raw_df['cycle_time'].mean():.1f} min
{snapshot}
---
Best‑practice notes (for internal reasoning, not for quoting):
{BEST_PRACTICE_NOTES}
---
Guidelines for your answer:
1. Start with the quantified answer.
2. Add one concise coaching insight.
3. Finish with an open follow‑up question.
4. If info is missing, ask for it.

User question: {question}
"""
    return prompt

# -------------------------------------------------------------------
# 3. Chat Interface
# -------------------------------------------------------------------
question = st.text_input("Ask the coach:")
if question:
    with st.spinner("Coach is thinking …"):
        prompt = build_prompt(question)
        client = OpenAI()
        rsp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":prompt}]
        )
        st.success("Coach says:")
        st.markdown(rsp.choices[0].message.content)

# -------------------------------------------------------------------
# 4. Optional Insights Button
# -------------------------------------------------------------------
if st.button("📈 Anomalies & Driver Performance"):
    st.subheader("Driver average cycle‑time (min)")
    st.bar_chart(raw_df.groupby("driver")["cycle_time"].mean())
