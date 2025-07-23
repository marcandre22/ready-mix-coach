# Streamlit Web App: CDWARE Coach – Ready-Mix (v3.1)

import streamlit as st
import pandas as pd
import random, uuid, json
from datetime import datetime, timedelta
import openai
from PIL import Image
import matplotlib.pyplot as plt

# -------------------------------------------------------------------
# 1. CONFIG & STYLING
# -------------------------------------------------------------------
openai.api_key = st.secrets["OPENAI_API_KEY"]
st.set_page_config(page_title="CDWARE Coach – Ready‑Mix", page_icon="🧱", layout="wide")

st.markdown(
    """
    <style>
        .main {background-color:#FFF9EF;}
        h1, h2, h3, .stMarkdown h1{color:#0F311C;}
        .stButton button{background-color:#E7662E;color:white;font-weight:bold;}
        .stButton button:hover{background-color:#cc541b;color:white;}
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------
# 2. SIMULATED DATA (15 July 2025)
# -------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def generate_data():
    truck_ids = [f"TRK-{i:03d}" for i in range(101, 111)]
    driver_names = [
        "John Tremblay", "Marc-Andre Gagnon", "Mary Bouchard", "Sebastian Leblanc",
        "Caroline Paquette", "Eric Fortin", "Lucy Martel", "Alexis Cote",
        "Patrick Morin", "Natalie Desrochers"
    ]
    driver_map = {t: random.choice(driver_names) for t in truck_ids}
    plants = ["Montreal Plant", "Quebec City Plant", "Laval Plant", "Sherbrooke Plant"]
    sites = ["Montreal Site", "Quebec City Site", "Laval Site", "Sherbrooke Site"]
    stages = ["dispatch", "loaded", "en_route", "waiting_at_site", "discharging", "washing", "back_to_plant"]
    rows, base_date = [], datetime(2025, 7, 15, 6, 0)

    for truck in truck_ids:
        for _ in range(random.randint(2, 4)):
            job_id = uuid.uuid4().hex[:8]
            start = base_date + timedelta(minutes=random.randint(0, 600))
            times, now = {}, start
            for stage in stages:
                times[stage] = now
                now += timedelta(minutes=random.randint(5, 30))

            row = {
                "truck_id": truck,
                "driver": driver_map[truck],
                "job_id": job_id,
                "origin_plant": random.choice(plants),
                "job_site": random.choice(sites),
                "cycle_time_min": round((now - start).total_seconds() / 60, 1),
                "water_added_liters": round(random.uniform(0, 120), 1),
                "drum_rpm": random.randint(4, 20),
                "hydraulic_pressure_psi": round(random.uniform(300, 1200), 1),
                "last_updated": "2025-07-15"
            }
            for i in range(len(stages)):
                row[f"time_{stages[i]}"] = times[stages[i]].strftime("%Y-%m-%d %H:%M:%S")
                if i > 0:
                    prev = stages[i - 1]
                    dur = (times[stages[i]] - times[prev]).total_seconds() / 60
                    row[f"dur_{stages[i]}"] = round(dur, 1)
            rows.append(row)

    return pd.DataFrame(rows)

raw_df = generate_data()

# -------------------------------------------------------------------
# 3. SIDEBAR
# -------------------------------------------------------------------
logo = Image.open("cdware_logo.png")
st.sidebar.image(logo, use_container_width=True)
st.sidebar.header("Options")
show_map = st.sidebar.checkbox("Show job‑site map")
show_table = st.sidebar.checkbox("Show data table", value=False)

st.sidebar.markdown("---")
with st.sidebar.expander("📖 Best‑Practice Handbook"):
    st.markdown("""
* **Target cycle‑time** ≤ 90 min (plant‑to‑plant).
* **Waiting at site** ≤ 10 min.
* **Water added** ≤ 40 L (unless QC override).
* **Staging tip**: Pre‑assign next job before *washing* stage.
* **Radio etiquette**: confirm *Loaded* & *Arrived* within 2 min.
* **Back‑to‑plant window**: keep gap < 20 min to maximise utilisation.
    """)

# -------------------------------------------------------------------
# 4. HEADER + COACH INPUT
# -------------------------------------------------------------------
st.markdown("## 🧠 CDWARE Coach – Ready‑Mix (v3.1)")
st.markdown("*Data‑driven coaching for dispatchers — 15 July 2025*")

st.markdown("### 🗨️ Ask a Question or Request Advice")
example_qs = [
    "Which driver had the most wait time at site?",
    "Suggest ways to reduce cycle time",
    "Which plant has the best average return rate?"
]
st.markdown("Try questions like:")
st.code("\n".join(example_qs), language="markdown")

user_question = st.text_input("Ask the coach:", placeholder="Type your question here…")

if user_question:
    with st.spinner("The coach is thinking…"):
        try:
            coach_guidelines = "You are a coach helping ready-mix dispatchers optimize fleet use. Reference best practices. Give helpful, clear answers using data."
            prompt = f"Context: {coach_guidelines}\n\nDATA:\n{raw_df.to_json(orient='records')}\n\nQUESTION: {user_question}"
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a Ready-Mix Dispatch Coach."},
                    {"role": "user", "content": prompt}
                ]
            )
            st.success("Coach’s Response")
            st.markdown(response.choices[0].message.content)
        except Exception as e:
            st.error(f"OpenAI error: {e}")

# -------------------------------------------------------------------
# 5. KPI DASHBOARD – with click-to-filter
# -------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("⏱️ Average Stage Durations (min)")
    stage_durs = raw_df[[c for c in raw_df.columns if c.startswith("dur_")]].mean().rename(lambda x: x.replace("dur_", ""))
    selected_stage = st.selectbox("Drill into stage:", stage_durs.index.tolist())
    st.bar_chart(stage_durs)
    if selected_stage:
        dur_col = f"dur_{selected_stage}"
        st.markdown(f"### 🔍 Drill-down: {selected_stage.capitalize()} by Driver")
        driver_breakdown = raw_df.groupby("driver")[dur_col].mean().sort_values()
        st.bar_chart(driver_breakdown)

with col2:
    st.subheader("🏭 Jobs per Plant")
    plant_counts = raw_df["origin_plant"].value_counts()
    selected_plant = st.selectbox("Drill into plant:", plant_counts.index.tolist())
    st.bar_chart(plant_counts)
    if selected_plant:
        st.markdown(f"### 🔍 Drill-down: {selected_plant} Job List")
        st.dataframe(raw_df[raw_df["origin_plant"] == selected_plant], use_container_width=True)

# -------------------------------------------------------------------
# 6. TABLE VIEW (optional)
# -------------------------------------------------------------------
if show_table:
    st.markdown("### 📊 Raw Job Data")
    st.dataframe(raw_df, use_container_width=True)

# -------------------------------------------------------------------
# 7. FOOTER
# -------------------------------------------------------------------
st.markdown("---")
st.markdown("© 2025 CDWARE Technologies Inc. | support@cdware.com")
