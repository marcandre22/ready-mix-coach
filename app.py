# app.py – Modern UI + Coach integration
import streamlit as st
import pandas as pd
import datetime
from openai import OpenAI

from dummy_data_gen import load_data
from coach_core import get_kpis, handle_simple_prompt
from instruction_set import GUIDELINES, SUGGESTED_PROMPTS
from tone_style import COACH_STYLE

st.set_page_config(page_title="CDWARE Ready‑Mix Coach", layout="wide")

# -------------------- HEADER --------------------
st.markdown("""
<div style='display:flex; justify-content:space-between; align-items:center; padding:8px 16px; background:black; color:white;'>
  <div style='font-weight:600;'>CDWare Technologies Inc</div>
  <div>{}</div>
</div>
""".format(datetime.datetime.now().strftime("%H:%M")), unsafe_allow_html=True)

# -------------------- SIDEBAR NAV --------------------
st.sidebar.title("Navigation")
tab = st.sidebar.radio("Select View", ["Reporting", "Chat"])

# -------------------- DATA LOAD + FILTER --------------------
if "tickets" not in st.session_state:
    st.session_state.tickets = load_data(days_back=7, n_jobs_per_day=80)

df = st.session_state.tickets.copy()

st.sidebar.subheader("Filters")
driver_filter = st.sidebar.selectbox("Driver", ["All"] + sorted(df["driver"].unique()))
plant_filter = st.sidebar.selectbox("Plant", ["All"] + sorted(df["origin_plant"].unique()))
date_filter = st.sidebar.date_input("Date", datetime.datetime.now().date())

if driver_filter != "All":
    df = df[df["driver"] == driver_filter]
if plant_filter != "All":
    df = df[df["origin_plant"] == plant_filter]
df = df[df["start_time"].dt.date == date_filter]

kpis = get_kpis(df, op_minutes=600)

# -------------------- REPORTING TAB --------------------
if tab == "Reporting":
    st.subheader("KPI Snapshot")
    col1, col2, col3 = st.columns(3)
    col1.metric("# Loads", kpis["loads_today"], "+5%")
    col2.metric("Avg Wait", f"{kpis['df_today']['dur_waiting'].mean():.1f} min", "-2%")
    col3.metric("Utilization", f"{kpis['utilization_pct']:.1f}%", "+3.2%")

    with st.expander("📊 KPI Report (TD)"):
        s = kpis["summary"]
        tbl = pd.DataFrame({
            "Description": [
                "Total m³", "Total Loads", "Avg Load Size", "First load (avg)", "Last load (avg)",
                "Jobs", "Trucks", "Loads/Truck", "Cycle time (avg min)",
                "Demurrage occurrences", "Excess wash", "Unscheduled stops"
            ],
            "Daily": [
                s["daily"]["m3"], s["daily"]["loads"], s["daily"]["avg_size"],
                s["daily"]["first_avg"], s["daily"]["last_avg"], s["daily"]["jobs"], s["daily"]["trucks"],
                f"{s['daily']['loads_per_truck']:.2f}", f"{s['daily']['cycle_avg']:.0f}",
                s["daily"]["demurrage"], s["daily"]["excess_wash"], s["daily"]["unscheduled"]
            ],
            "WTD": [
                s["wtd"]["m3"], s["wtd"]["loads"], s["wtd"]["avg_size"], s["wtd"]["first_avg"], s["wtd"]["last_avg"],
                s["wtd"]["jobs"], s["wtd"]["trucks"], f"{s['wtd']['loads_per_truck']:.2f}", f"{s['wtd']['cycle_avg']:.0f}",
                s["wtd"]["demurrage"], s["wtd"]["excess_wash"], s["wtd"]["unscheduled"]
            ],
            "MTD": [
                s["mtd"]["m3"], s["mtd"]["loads"], s["mtd"]["avg_size"], s["mtd"]["first_avg"], s["mtd"]["last_avg"],
                s["mtd"]["jobs"], s["mtd"]["trucks"], f"{s['mtd']['loads_per_truck']:.2f}", f"{s['mtd']['cycle_avg']:.0f}",
                s["mtd"]["demurrage"], s["mtd"]["excess_wash"], s["mtd"]["unscheduled"]
            ],
        })
        st.dataframe(tbl, use_container_width=True)

    st.subheader("🚚 Fleet Productivity")
    df_today = kpis["df_today"][["truck", "min_total", "min_prod", "prod_ratio"]].copy()
    st.dataframe(df_today.rename(columns={
        "truck": "Truck",
        "min_total": "Shift (min)",
        "min_prod": "Prod (min)",
        "prod_ratio": "Prod %"
    }))

    with st.expander("📍 Geofence Dwell Times (Plant & Site)"):
        df_dwell = kpis["df_today"][
            ["truck", "plant_in", "plant_out", "plant_dwell", "site_in", "site_out", "site_dwell"]
        ].sort_values("plant_in")

        df_dwell = df_dwell.rename(columns={
            "truck": "Truck",
            "plant_in": "Plant In",
            "plant_out": "Plant Out",
            "plant_dwell": "Plant Dwell (min)",
            "site_in": "Site In",
            "site_out": "Site Out",
            "site_dwell": "Site Dwell (min)",
        })

        st.dataframe(df_dwell, use_container_width=True)

# -------------------- CHAT TAB --------------------
elif tab == "Chat":
    st.markdown("## Ask your coach a question")
    if "chat" not in st.session_state:
        st.session_state.chat = []

    def process_user_question(q: str):
        st.session_state.chat.append({"role": "user", "msg": q})
        quick = handle_simple_prompt(q, kpis)
        if quick:
            reply = quick
        else:
            reply = OpenAI().chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": q}]
            ).choices[0].message.content
        st.session_state.chat.append({"role": "assistant", "msg": reply})

    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["msg"])

    user_q = st.chat_input("Type your question …")
    if user_q:
        process_user_question(user_q)
        st.experimental_rerun()

    st.markdown("### Suggested questions:")
    for q in SUGGESTED_PROMPTS[:5]:
        st.markdown(f"<div style='color:gray'>• {q}</div>", unsafe_allow_html=True)
        if st.button(q, key=f"suggest_{q}"):
            process_user_question(q)
            st.experimental_rerun()
