# app.py – Ready‑Mix Coach with productivity dashboard
# -----------------------------------------------------
# Key additions:
# • Uses updated dummy_data_gen with ignition timestamps
# • Shows fleet‑level productivity (pie & metrics)
# • Integrates coach_core v2 for quick answers
# -----------------------------------------------------

import streamlit as st
from openai import OpenAI
import pandas as pd

from dummy_data_gen import load_data
from coach_core import get_kpis, handle_simple_prompt
from instruction_set import GUIDELINES, SUGGESTED_PROMPTS
from tone_style import COACH_STYLE

st.set_page_config(page_title="CDWARE Ready‑Mix Coach", layout="wide", initial_sidebar_state="expanded")
st.title("CDWARE Ready‑Mix Coach")

# -----------------------------------------------------
# 1. Load / cache data
# -----------------------------------------------------
if "tickets" not in st.session_state:
    st.session_state.tickets = load_data(days_back=7, n_jobs_per_day=80)

df = st.session_state.tickets.copy()

# -----------------------------------------------------
# 2. KPI extraction
# -----------------------------------------------------
kpis = get_kpis(df, op_minutes=600)  # 10h default

# -----------------------------------------------------
# 3. Sidebar – preview + benchmark quick prompts
# -----------------------------------------------------
with st.sidebar:
    st.header("Sample data")
    if st.checkbox("Show raw rows"):
        st.dataframe(df.head(50), use_container_width=True)

    st.markdown("---")
    st.subheader("Quick questions")
    for p in SUGGESTED_PROMPTS[:15]:
        if st.button(p, key=f"q_{p}"):
            st.session_state.inject_q = p

# -----------------------------------------------------
# 4. KPI snapshots (today)
# -----------------------------------------------------
col1, col2, col3 = st.columns(3)
col1.metric("Loads", kpis["loads_today"])
col2.metric("Cycle (avg min)", f"{kpis['cycle_today']:.1f}")
col3.metric("Utilization", f"{kpis['utilization_pct']:.1f}%")

# -----------------------------------------------------
# 5. Productivity expander
# -----------------------------------------------------
with st.expander("🚚 Fleet productivity (today)"):
    pr = kpis["prod_ratio"]
    st.metric("Productive vs Idle", f"{pr:.1f}% productive")

    # Bar
    prod = kpis["prod_prod_min"] / 60
    idle = kpis["prod_idle_min"] / 60
    st.progress(min(int(pr),100))
    st.caption(f"≈ {prod:,.1f} h productive, {idle:,.1f} h idle")

    # Truck table
    df_today = kpis["df_today"][["truck","min_total","min_prod","prod_ratio"]].sort_values("prod_ratio", ascending=False)
    st.dataframe(df_today.rename(columns={
        "truck":"Truck",
        "min_total":"Shift (min)",
        "min_prod":"Prod (min)",
        "prod_ratio":"Prod %"}), use_container_width=True)

# -----------------------------------------------------
# 6. Chat interface
# -----------------------------------------------------
if "chat" not in st.session_state:
    st.session_state.chat = []

for item in st.session_state.chat:
    with st.chat_message(item["role"]):
        st.markdown(item["msg"])

# Build prompt helper
snapshot = (f"Loads today {kpis['loads_today']}, avg cycle {kpis['cycle_today']:.1f} min, "
            f"fleet productive ratio {kpis['prod_ratio']:.1f}%.")

def build_prompt(q: str):
    mem = "\n".join(f"{m['role'].title()}: {m['msg']}" for m in st.session_state.chat[-4:])
    return f"{COACH_STYLE}\n{GUIDELINES}\n{snapshot}\n{mem}\nQuestion: {q}"

inject = st.session_state.pop("inject_q", "") if "inject_q" in st.session_state else ""
user_q = st.chat_input(inject or "Ask the coach …")

if user_q:
    with st.chat_message("user"):
        st.markdown(user_q)

    quick = handle_simple_prompt(user_q, kpis)
    if quick:
        reply = quick
    else:
        with st.spinner("Thinking …"):
            reply = OpenAI().chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": build_prompt(user_q)}]
            ).choices[0].message.content

    with st.chat_message("assistant"):
        st.markdown(reply)

    st.session_state.chat.extend([
        {"role":"user","msg":user_q},
        {"role":"assistant","msg":reply}
    ])
