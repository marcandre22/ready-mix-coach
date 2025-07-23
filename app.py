# Streamlit Web App: **CDWARE Coach – Ready‑Mix (v3)**
# Run with: `streamlit run app.py`
"""
NEW IN v3
---------
1. **Extra KPIs**
   • *Stage‑duration breakdown* – avg minutes spent in each cycle stage (stacked bar).
   • *Jobs per plant* – throughput view (bar chart).
   • *Water‑added compliance* – histogram with target band (≤ 40 L).
2. **Embedded Best‑Practice Handbook**
   Side panel with curated tips for ready‑mix dispatchers (cycle‑time cadences, staging, radio etiquette, etc.).
3. **Enhanced GPT‑4 prompt** – model now references best‑practice guidelines to tailor advice.

Dependencies (add to `requirements.txt` if missing):
```
streamlit
pandas
openai>=1.0.0
pydeck
matplotlib
```
"""

import streamlit as st
import pandas as pd
import random, uuid, json
from datetime import datetime, timedelta
import openai
from PIL import Image
import matplotlib.pyplot as plt

# -------------------------------------------------------------------
# 1. CONFIG & PAGE STYLE
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
# 2. DATA GENERATOR (cached) – fixed 15 July 2025
# -------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def generate_data():
    random.seed(42)

    truck_ids = [f"TRK-{i:03d}" for i in range(101, 111)]
    drivers = [
        "John Tremblay", "Marc-Andre Gagnon", "Mary Bouchard", "Sebastian Leblanc",
        "Caroline Paquette", "Eric Fortin", "Lucy Martel", "Alexis Cote",
        "Patrick Morin", "Natalie Desrochers"
    ]
    driver_map = {t: random.choice(drivers) for t in truck_ids}

    plants = [
        "Montreal Plant", "Quebec City Plant", "Laval Plant", "Sherbrooke Plant",
        "Trois-Rivieres Plant", "Gatineau Plant"
    ]
    sites = [
        "Montreal Site", "Quebec City Site", "Laval Site", "Sherbrooke Site",
        "Trois-Rivieres Site", "Saguenay Site", "Drummondville Site"
    ]
    coords = {
        "Montreal Site": (45.5019, -73.5674), "Quebec City Site": (46.8139, -71.2080),
        "Laval Site": (45.6066, -73.7124), "Sherbrooke Site": (45.4042, -71.8929),
        "Trois-Rivieres Site": (46.3420, -72.5478), "Saguenay Site": (48.4183, -71.0589),
        "Drummondville Site": (45.8847, -72.4860),
    }

    stages = ["dispatch", "loaded", "en_route", "waiting_at_site", "discharging", "washing", "back_to_plant"]

    rows, base = [], datetime(2025, 7, 15, 6, 0)
    for t in truck_ids:
        for _ in range(random.randint(2, 4)):
            job_id = uuid.uuid4().hex[:8]
            start = base + timedelta(minutes=random.randint(0, 600))
            now   = start
            times = {}
            for stage in stages:
                times[stage] = now
                now += timedelta(minutes=random.randint(5, 30))
            site = random.choice(sites)
            lat, lon = coords[site]
            rows.append({
                "truck_id": t,
                "driver": driver_map[t],
                "job_id": job_id,
                "origin_plant": random.choice(plants),
                "job_site": site, "lat": lat, "lon": lon,
                "cycle_time_min": round((now - start).total_seconds()/60, 1),
                "water_added_liters": round(random.uniform(0, 120), 1),
                "drum_rpm": random.randint(4, 20),
                "hydraulic_pressure_psi": round(random.uniform(300, 1200), 1),
                **{f"time_{s}": times[s] for s in stages},
                "last_updated": "2025-07-15",
            })
    return pd.DataFrame(rows)

raw_df = generate_data()

# Derived metrics
raw_df["wait_min"] = (raw_df["time_discharging"] - raw_df["time_waiting_at_site"]).dt.total_seconds()/60
stage_cols = [f"time_{s}" for s in ["dispatch", "loaded", "en_route", "waiting_at_site", "discharging", "washing", "back_to_plant"]]
for i in range(1, len(stage_cols)):
    stage_name = stage_cols[i].replace("time_", "dur_")
    raw_df[stage_name] = (raw_df[stage_cols[i]] - raw_df[stage_cols[i-1]]).dt.total_seconds()/60

# -------------------------------------------------------------------
# 3. SIDEBAR – Logo, toggles, best‑practice handbook
# -------------------------------------------------------------------
logo = Image.open("cdware_logo.png")
st.sidebar.image(logo, use_container_width=True)

st.sidebar.header("Options")
show_map   = st.sidebar.checkbox("Show job‑site map")
show_table = st.sidebar.checkbox("Show full table", value=False)

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
# 4. HEADER & DATA PREVIEW
# -------------------------------------------------------------------
st.markdown("## 🧠 CDWARE Coach – Ready‑Mix (v3)")
st.markdown("*Data‑driven coaching for dispatchers — 15 July 2025*")

st.dataframe(raw_df if show_table else raw_df.head(20), use_container_width=True)

# -------------------------------------------------------------------
# 5. KPI DASHBOARD
# -------------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    st.subheader("⏱️ Average Stage Durations (min)")
    stage_durs = raw_df[[c for c in raw_df.columns if c.startswith("dur_")]].mean().rename(lambda x: x.replace("dur_", ""))
    st.bar_chart(stage_durs)

with col2:
    st.subheader("🏭 Jobs per Plant")
    plant_counts = raw_df["origin_plant"].value_counts()
    st.bar_chart(plant_counts)

st.subheader("💧 Water‑Added Compliance (histogram)")
fig, ax = plt.subplots(figsize=(6,3))
ax.hist(raw_df["water_added_liters"], bins=15)
ax.axvline(40, color="red", linestyle="--", label="40 L target")
ax.set_xlabel("Litres added")
ax.legend()
st.pyplot(fig, use_container_width=True)

# -------------------------------------------------------------------
# 6. MAP VIEW
# -------------------------------------------------------------------
if show_map:
    st.subheader("📍 Job‑Site Map")
    st.map(raw_df[["lat", "lon"]])

# -------------------------------------------------------------------
# 7. GPT‑4 COACH with Best‑Practice Context
# -------------------------------------------------------------------
coach_guidelines = (
    "Target cycle‑time ≤90 min, waiting‑at‑site ≤10 min, water ≤40 L. Staging before washing. "
    "Provide 3 concise, numbered recommendations with rationale."
)

if st.button("💡 Generate AI Recommendations"):
    with st.spinner("Analysing & coaching…"):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": coach_guidelines},
                    {"role": "user", "content": raw_df.to_json(orient="records")}
                ]
            )
            st.success("AI Coach Recommendations")
            st.markdown(response.choices[0].message.content)
        except Exception as e:
            st.error(f"OpenAI error: {e}")

# -------------------------------------------------------------------
# 8. FOOTER
# -------------------------------------------------------------------
st.markdown("---")
st.markdown("© 2025 CDWARE Technologies Inc. | support@cdware.com")
