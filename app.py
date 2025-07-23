# Ready‑Mix Coach – CDWARE (v3.9)
# English‑only. Expanded dataset with richer telematics fields.

import streamlit as st
import pandas as pd
import random
from openai import OpenAI
from datetime import datetime, timedelta
from io import BytesIO

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

# --- Embedded best‑practice cheat‑sheet (internal only) ---
BEST_PRACTICE = """Key operational principles distilled from *Make It Happen* (full internal digest):
• Pre‑pour alignment – confirm mix, slump, target volume, site access, and pump readiness prior to dispatch.
• Loading excellence – loaders aim for ≤ 7 minutes, verify ticket, release air, spin drum at ≥ 4 rpm.
• Predictive ETAs – send automatic 50 % and 90 % arrival alerts; recalc in traffic.
• In‑route quality – monitor water additions (< 40 L) and hydraulic pressure to avoid segregation.
• Site flow – a truck should start discharging ≤ 2 minutes after arrival; escalate if waiting > 10 min.
• Post‑wash loop – record wash end‑time, fuel used, anomalies, and push cycle KPIs by shift end.
• Continuous improvement – daily stand‑ups review average stage times, outliers, and driver feedback."""

# -------------------------------------------------------------------
# 1. Generate richer simulated telematics / ERP data
# -------------------------------------------------------------------
@st.cache_data

def load_data(n_jobs: int = 50):
    drivers = ["Marc", "Julie", "Antoine", "Sarah", "Luc", "Melanie", "Simon", "Elise"]
    plants  = ["Montreal", "Laval", "Quebec", "Drummondville"]
    sites   = ["Longueuil", "Trois‑Rivieres", "Sherbrooke", "Repentigny"]

    rows = []
    base_time = datetime(2025, 7, 15, 5, 0)

    for i in range(n_jobs):
        start = base_time + timedelta(minutes=random.randint(0, 600))
        d_dispatch   = random.randint(8, 20)
        d_loaded     = random.randint(4, 9)
        d_en_route   = random.randint(12, 35)
        d_waiting    = random.randint(3, 15)
        d_disch      = random.randint(8, 18)
        d_wash       = random.randint(4, 9)
        d_back       = random.randint(8, 22)
        durs = [d_dispatch,d_loaded,d_en_route,d_waiting,d_disch,d_wash,d_back]

        water_added = round(random.uniform(0, 120),1)
        rpm         = random.randint(3, 15)
        pressure    = random.randint(300, 1200)
        fuel_used   = round(random.uniform(8, 30),1)  # litres
        avg_speed   = round(random.uniform(35, 65),1) # km/h while en‑route

        row = {
            "job_id"       : f"J{1000+i}",
            "driver"       : random.choice(drivers),
            "origin_plant" : random.choice(plants),
            "job_site"     : random.choice(sites),
            "start_time"   : start.strftime("%Y-%m-%d %H:%M"),
            "cycle_time"   : sum(durs),
            "water_added_L": water_added,
            "drum_rpm"     : rpm,
            "hyd_press_PSI": pressure,
            "fuel_L"       : fuel_used,
            "avg_speed_kmh": avg_speed,
        }
        stages = ["dispatch","loaded","en_route","waiting","discharging","washing","back"]
        for s,v in zip(stages,durs):
            row[f"dur_{s}"] = v
        rows.append(row)
    return pd.DataFrame(rows)

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
# 2. Prompt builder with richer metrics
# -------------------------------------------------------------------

def build_prompt(q:str)->str:
    kpis = {
        "avg_cycle": f"{raw_df['cycle_time'].mean():.1f} min",
        "avg_wait": f"{raw_df['dur_waiting'].mean():.1f} min",
        "avg_load": f"{raw_df['dur_loaded'].mean():.1f} min",
        "avg_water": f"{raw_df['water_added_L'].mean():.1f} L",
        "avg_rpm": f"{raw_df['drum_rpm'].mean():.1f} rpm"
    }
    snap = "\n".join([f"- {k.replace('_',' ').title()}: {v}" for k,v in kpis.items()])

    prompt = f"""You are an expert ready‑mix dispatch coach.
Use the telematics snapshot and internal best‑practice knowledge. NEVER quote the notes directly.

Snapshot:
Jobs: {len(raw_df)}
{snap}

Best‑practice summary (internal): {BEST_PRACTICE}

Guidelines:
1. State the numerical answer.
2. Give one insight.
3. Ask a follow‑up question.
4. Request missing info if needed.

Question: {q}
"""
    return prompt

# -------------------------------------------------------------------
# 3. Chat interface
# -------------------------------------------------------------------
q = st.text_input("Ask the coach:")
if q:
    with st.spinner("Thinking…"):
        client = OpenAI()
        out = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":build_prompt(q)}]
        )
        st.markdown(out.choices[0].message.content)

# -------------------------------------------------------------------
# 4. Quick insights button
# -------------------------------------------------------------------
if st.button("📈 KPI Charts"):
    st.subheader("Average stage durations (min)")
    st.bar_chart(raw_df.filter(like="dur_").mean())
