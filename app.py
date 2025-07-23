# Streamlit Web App: CDWARE Coach – Ready-Mix
# Run with: streamlit run app.py

import streamlit as st
import openai
import json
from PIL import Image

# Set your OpenAI API key securely
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Load and show CDWARE logo
logo = Image.open("cdware_logo.png")
st.sidebar.image(logo, use_container_width=True)

# Page configuration and CDWARE styling
st.set_page_config(page_title="CDWARE Coach – Ready-Mix", page_icon="🧱", layout="wide")

# --- Custom styling with CDWARE brand colors ---
st.markdown(
    """
    <style>
        .main {
            background-color: #FFF9EF;
        }
        h1, h2, h3, .stMarkdown h1 {
            color: #0F311C;
        }
        .stButton button {
            background-color: #E7662E;
            color: white;
            font-weight: bold;
        }
        .stButton button:hover {
            background-color: #cc541b;
            color: white;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# --- App Header ---
st.markdown("## 🧠 CDWARE Coach – Ready-Mix")
st.markdown("*Your smart assistant for optimizing fleet performance and operational insights.*")

# --- Input form ---
st.sidebar.header("Simulated Data Input")
fleet_utilization = st.sidebar.slider("Current Fleet Utilization (%)", 0, 100, 72)
target_utilization = st.sidebar.slider("Target Fleet Utilization (%)", 0, 100, 85)

truck_data = [
    {"id": 101, "status": "idle", "location": "plant", "idle_time_min": 35, "jobs_completed": 3},
    {"id": 105, "status": "on_delivery", "location": "construction_site", "cycle_stage": "discharging", "jobs_completed": 4},
    {"id": 112, "status": "idle", "location": "plant", "idle_time_min": 15, "jobs_completed": 2}
]

jobs_today = 12
jobs_target = 18

# Compose the input data
input_data = {
    "fleet_utilization": fleet_utilization,
    "target_utilization": target_utilization,
    "trucks": truck_data,
    "jobs_today": jobs_today,
    "jobs_target": jobs_target,
    "time_now": "1:15 PM"
}

# --- Prompt configuration ---
system_prompt = (
    "You are a Ready-Mix Dispatch Coach. Your job is to analyze fleet utilization and truck data "
    "and give simple, actionable advice to dispatchers on how to improve fleet usage, reduce idle time, "
    "and meet their utilization targets. Speak clearly and provide 2-3 practical recommendations per answer."
)

user_prompt = f"Analyze the following data and give recommendations to improve fleet utilization this afternoon:\n{json.dumps(input_data, indent=2)}"

# --- Button to run the analysis ---
if st.button("💡 Generate Recommendations"):
    try:
        with st.spinner("Thinking like a dispatch coach..."):
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            answer = response.choices[0].message.content
            st.success("Here are your AI recommendations:")
            st.markdown(answer)
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

# --- Display raw input for debug/testing ---
with st.expander("🔍 Show Simulated Data"):
    st.json(input_data)

# --- CDWARE Footer ---
st.markdown("---")
st.markdown("© 2025 CDWARE Technologies Inc. | Contact: support@cdware.com")
