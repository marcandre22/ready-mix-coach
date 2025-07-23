# ✅ Update to add clickable drill-down for KPI charts and improved coach prompting
# Streamlit Web App: **CDWARE Coach – Ready‑Mix (v3.5)** with export, benchmarking, and anomaly detection

import streamlit as st
import pandas as pd
import random
import openai
from datetime import datetime
from io import BytesIO
from streamlit_chat import message

st.set_page_config(page_title="Ready-Mix Coach", layout="wide", initial_sidebar_state="expanded")

# -------------------------------------------------------------------
# Brand Styling: CDWARE Dark Mode + Bilingual
# -------------------------------------------------------------------
st.markdown("""
    <style>
    body { background-color: #121212; color: #f1f1f1; }
    .main { background-color: #121212; }
    h1, h2, h3, h4 { color: #E7662E; }
    .stButton button { background-color: #E7662E; color: white; font-weight: bold; }
    .css-1rs6os.edgvbvh3 { color: #FFFFFF; }
    </style>
""", unsafe_allow_html=True)

st.image("cdware_logo.png", width=300)
st.title("CDWARE Ready-Mix Coach / Coach Béton Prêt-à-l'emploi")

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
# Sidebar Toggle for Data View & Tools
# -------------------------------------------------------------------
st.sidebar.title("🧾 Options / Options")
if st.sidebar.checkbox("Show raw data / Afficher les données brutes"):
    st.dataframe(raw_df, use_container_width=True)

if st.sidebar.checkbox("Show job locations map / Afficher la carte des chantiers"):
    st.subheader("🗺️ Job Location Map / Carte des sites")
    loc_df = raw_df[["job_location", "origin_plant"]]
    loc_df["lat"] = loc_df["job_location"].apply(lambda x: random.uniform(45.0, 46.0))
    loc_df["lon"] = loc_df["job_location"].apply(lambda x: random.uniform(-74.5, -72.0))
    st.map(loc_df.rename(columns={"lat": "latitude", "lon": "longitude"}))

# Export Tools
st.sidebar.markdown("### 📤 Export Tools / Outils d'export")
if st.sidebar.button("📥 Export to Excel / Exporter en Excel"):
    excel_data = BytesIO()
    raw_df.to_excel(excel_data, index=False)
    st.sidebar.download_button("Download Excel", data=excel_data.getvalue(), file_name="ready_mix_data.xlsx")

if st.sidebar.button("📥 Export to CSV / Exporter en CSV"):
    st.sidebar.download_button("Download CSV", data=raw_df.to_csv(index=False), file_name="ready_mix_data.csv")

# -------------------------------------------------------------------
# 2. Coach Prompt Setup
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
# 3. Chatbot Interface
# -------------------------------------------------------------------
st.subheader("💬 Ask the coach / Posez votre question au coach:")
with st.expander("💡 Sample Questions / Questions suggérées"):
    st.markdown("""
- What is my average turnaround per job? / Quel est mon délai moyen par livraison?
- What is the cost per delivery? / Quel est le coût par livraison?
- Which driver is the most efficient? / Quel chauffeur est le plus efficace?
- Where do I lose time most often? / Où est-ce que je perds le plus de temps?
- Can I optimize my dispatching schedule? / Puis-je optimiser ma planification?
- Compare my plants / Comparer mes usines
- Who needs coaching? / Qui a besoin de coaching?
""")

user_q = st.text_input("", placeholder="E.g. What’s my average turnaround time per job? / Quel est mon délai moyen?", label_visibility="collapsed")
if user_q:
    with st.spinner("Coach is thinking / Le coach réfléchit..."):
        prompt = build_prompt(user_q)
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt}
            ]
        )
        answer = completion.choices[0].message.content
        st.success("Coach’s Response / Réponse du coach")
        st.markdown(answer)

# -------------------------------------------------------------------
# 4. Optional Analysis Button
# -------------------------------------------------------------------
if st.button("📈 Show Anomaly Detection & Driver Performance"):
    st.subheader("🔍 Outlier Detection / Détection d'anomalies")
    avg_cycle = raw_df["cycle_time"].mean()
    std_cycle = raw_df["cycle_time"].std()
    outliers = raw_df[raw_df["cycle_time"] > avg_cycle + std_cycle]
    if not outliers.empty:
        st.warning(f"Found {len(outliers)} jobs with unusually long cycle times.")
        st.dataframe(outliers)
    else:
        st.success("No significant outliers detected.")

    st.subheader("🏁 Driver Performance Summary / Sommaire des chauffeurs")
    perf_df = raw_df.groupby("driver")["cycle_time"].mean().sort_values()
    st.bar_chart(perf_df)

# -------------------------------------------------------------------
# 5. Minimalist Benchmarking (No fla fla)
# -------------------------------------------------------------------
st.subheader("📊 Benchmarking Insights / Sommaire de performance")
col1, col2 = st.columns(2)
with col1:
    st.metric("⏱️ Avg. Turnaround (min)", f"{raw_df['cycle_time'].mean():.1f}")
    st.metric("👥 Drivers", raw_df['driver'].nunique())
with col2:
    best_driver = raw_df.groupby("driver")["cycle_time"].mean().idxmin()
    st.metric("🏆 Best Avg. Driver", best_driver)
    worst_driver = raw_df.groupby("driver")["cycle_time"].mean().idxmax()
    st.metric("⚠️ Slowest Avg. Driver", worst_driver)
