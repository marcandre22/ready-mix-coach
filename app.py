# ✅ Update to add clickable drill-down for KPI charts and improved coach prompting
# Streamlit Web App: **CDWARE Coach – Ready‑Mix (v3.2)**

import streamlit as st
import pandas as pd
import random
import openai
from datetime import datetime
from streamlit_chat import message

st.set_page_config(page_title="Ready-Mix Coach", layout="wide")
st.markdown("""
    <style>
    .main {background-color: #FFF9F0;}
    h1, h2, h3, h4 {color: #0F311C;}
    .stButton button {background-color: #E7662E; color: white; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

st.image("cdware_logo.png", width=300)
st.title("CDWARE Ready-Mix Coach")

# -------------------------------------------------------------------
# 1. Load Simulated Data
# -------------------------------------------------------------------
@st.cache_data
def load_data():
    names = ["Marc", "Julie", "Antoine", "Sarah", "Luc", "Mélanie", "Simon", "Élise"]
    stages = ["dispatch", "loaded", "en_route", "waiting", "discharging", "washing", "back"]
    plants = ["Montreal", "Laval", "Quebec", "Drummondville"]
    locations = ["Longueuil", "Trois-Rivières", "Sherbrooke", "Repentigny"]
    data = []
    for i in range(28):
        job = {
            "job_id": f"J-{1000+i}",
            "driver": random.choice(names),
            "origin_plant": random.choice(plants),
            "job_location": random.choice(locations),
            "date": datetime(2024, 7, 15)
        }
        durations = [random.randint(10, 25),  # dispatch
                     random.randint(5, 10),   # loaded
                     random.randint(15, 30),  # en_route
                     random.randint(5, 20),   # waiting
                     random.randint(10, 20),  # discharging
                     random.randint(5, 10),   # washing
                     random.randint(10, 25)]  # back
        for j, s in enumerate(stages):
            job[f"dur_{s}"] = durations[j]
        job["cycle_time"] = sum(durations)
        data.append(job)
    return pd.DataFrame(data)

raw_df = load_data()

# -------------------------------------------------------------------
# 2. Sidebar Toggle for Data View
# -------------------------------------------------------------------
st.sidebar.title("🧾 Options")
if st.sidebar.checkbox("Show raw data"):
    st.dataframe(raw_df, use_container_width=True)

# -------------------------------------------------------------------
# 3. Coach Prompt Setup
# -------------------------------------------------------------------
def build_prompt(user_input):
    prompt = f"""
You are a ready-mix fleet operations coach. Your job is to respond in a helpful, concise, and coaching tone to ready-mix dispatchers and fleet managers.

1. Provide the direct answer first (quantified or visual).
2. Follow up with one short explanation that adds insight.
3. End with an open-ended follow-up question to teach the user something about dispatch best practices.
4. If the user’s question cannot be answered due to missing information (e.g., cost per delivery but no hourly rate), ask for that info before continuing.
5. Do NOT include full calculation steps unless explicitly asked.

User question:
""" + user_input + """

Using this context, respond with coaching insight and suggest improvements.
"""
    return prompt

# -------------------------------------------------------------------
# 4. Chatbot Interface
# -------------------------------------------------------------------
st.subheader("💬 Ask the coach:")
user_q = st.text_input("", placeholder="E.g. What’s my average turnaround time per job?", label_visibility="collapsed")
if user_q:
    with st.spinner("Coach is thinking..."):
        prompt = build_prompt(user_q)
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt}
            ]
        )
        answer = completion.choices[0].message.content
        st.success("Coach’s Response")
        st.markdown(answer)

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
# 6. Optional Map Tool
# -------------------------------------------------------------------
if st.sidebar.checkbox("Show job locations map"):
    st.subheader("🗺️ Job Location Map")
    loc_df = raw_df[["job_location", "origin_plant"]]
    loc_df["lat"] = loc_df["job_location"].apply(lambda x: random.uniform(45.0, 46.0))
    loc_df["lon"] = loc_df["job_location"].apply(lambda x: random.uniform(-74.5, -72.0))
    st.map(loc_df.rename(columns={"lat": "latitude", "lon": "longitude"}))
