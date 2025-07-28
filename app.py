from prompt_utils import build_system_prompt
# app.py – Ready‑Mix Coach with KPI summary & quick‑prompt auto‑send
import streamlit as st
from openai import OpenAI

from dummy_data_gen import load_data
from coach_core import get_kpis, handle_simple_prompt
from instruction_set import GUIDELINES, SUGGESTED_PROMPTS
from tone_style import COACH_STYLE

st.set_page_config(page_title="CDWARE Ready‑Mix Coach", layout="wide", initial_sidebar_state="expanded")
st.title("CDWARE Ready‑Mix Coach")

# -------------------------------------------------------------------
# 1. Data cache
# -------------------------------------------------------------------
if "tickets" not in st.session_state:
    st.session_state.tickets = load_data(days_back=7, n_jobs_per_day=80)

df = st.session_state.tickets.copy()

# -------------------------------------------------------------------
# 2. KPIs
# -------------------------------------------------------------------
kpis = get_kpis(df, op_minutes=600)

# -------------------------------------------------------------------
# 3. Sidebar – data preview + quick prompts
# -------------------------------------------------------------------
with st.sidebar:
    st.header("Sample data")
    if st.checkbox("Show raw rows"):
        st.dataframe(df.head(40), use_container_width=True)

    st.markdown("---")
    st.subheader("Quick questions")

    def _send_q(q):
        process_user_question(q)
        st.experimental_rerun()

    for p in SUGGESTED_PROMPTS[:15]:
        if st.button(p, key=f"q_{p}"):
            _send_q(p)

# -------------------------------------------------------------------
# 4. KPI snapshot (today)
# -------------------------------------------------------------------
col1, col2, col3 = st.columns(3)
col1.metric("Loads", kpis["loads_today"])
col2.metric("Cycle (avg min)", f"{kpis['cycle_today']:.1f}")
col3.metric("Utilization", f"{kpis['utilization_pct']:.1f}%")

# -------------------------------------------------------------------
# 5. KPI Report (Daily / WTD / MTD / YTD)
# -------------------------------------------------------------------
with st.expander("📊 KPI Report (TD)"):
    s = kpis["summary"]
    import pandas as pd
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
        "Weekly(TD)": [
            s["wtd"]["m3"], s["wtd"]["loads"], s["wtd"]["avg_size"],
            s["wtd"]["first_avg"], s["wtd"]["last_avg"], s["wtd"]["jobs"], s["wtd"]["trucks"],
            f"{s['wtd']['loads_per_truck']:.2f}", f"{s['wtd']['cycle_avg']:.0f}",
            s["wtd"]["demurrage"], s["wtd"]["excess_wash"], s["wtd"]["unscheduled"]
        ],
        "Monthly(TD)": [
            s["mtd"]["m3"], s["mtd"]["loads"], s["mtd"]["avg_size"],
            s["mtd"]["first_avg"], s["mtd"]["last_avg"], s["mtd"]["jobs"], s["mtd"]["trucks"],
            f"{s['mtd']['loads_per_truck']:.2f}", f"{s['mtd']['cycle_avg']:.0f}",
            s["mtd"]["demurrage"], s["mtd"]["excess_wash"], s["mtd"]["unscheduled"]
        ],
        "Yearly(TD)": [
            s["ytd"]["m3"], s["ytd"]["loads"], s["ytd"]["avg_size"],
            s["ytd"]["first_avg"], s["ytd"]["last_avg"], s["ytd"]["jobs"], s["ytd"]["trucks"],
            f"{s['ytd']['loads_per_truck']:.2f}", f"{s['ytd']['cycle_avg']:.0f}",
            s["ytd"]["demurrage"], s["ytd"]["excess_wash"], s["ytd"]["unscheduled"]
        ],
    })
    st.dataframe(tbl, use_container_width=True)

# -------------------------------------------------------------------
# 6. Productivity section (same as before)
# -------------------------------------------------------------------
with st.expander("🚚 Fleet productivity (today)"):
    pr = kpis["prod_ratio"]
    st.metric("Productive vs Idle", f"{pr:.1f}% productive")
    st.progress(min(int(pr), 100))
    prod_h = kpis["prod_prod_min"] / 60
    idle_h = kpis["prod_idle_min"] / 60
    st.caption(f"≈ {prod_h:.1f} h productive, {idle_h:.1f} h idle")

    df_today = (
        kpis["df_today"][["truck", "min_total", "min_prod", "prod_ratio"]]
        .sort_values("prod_ratio", ascending=False)
        .rename(columns={
            "truck": "Truck", "min_total": "Shift (min)", "min_prod": "Prod (min)", "prod_ratio": "Prod %"})
    )

    st.dataframe(
        df_today,
        column_config={
            "Shift (min)": st.column_config.NumberColumn(help="Total engine‑on time (Ignition ON → OFF)"),
            "Prod (min)":  st.column_config.NumberColumn(help="Minutes delivering loads (1st Ticket → Last Return)"),
            "Prod %":      st.column_config.NumberColumn(help="Prod (min) ÷ Shift (min) × 100"),
        },
        use_container_width=True,
    )

# 6b. Geofence Dwell Times
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


# -------------------------------------------------------------------
# 7. Chat helpers
# -------------------------------------------------------------------
if "chat" not in st.session_state:
    st.session_state.chat = []


def process_user_question(q: str):
    """Send the question through the same pipeline as manual input."""
    st.session_state.chat.append({"role": "user", "msg": q})
    quick = handle_simple_prompt(q, kpis)
    if quick:
        reply = quick
    else:
        reply = OpenAI().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": build_prompt(q)}]
        ).choices[0].message.content
    st.session_state.chat.append({"role": "assistant", "msg": reply})

# Render history
for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["msg"])

# Chat input
user_q = st.chat_input("Type your question …")
if user_q:
    process_user_question(user_q)
    st.experimental_rerun()
