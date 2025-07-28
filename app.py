# app.py  –  Ready-Mix Coach  (v3.16)
# -----------------------------------
# • Multi-day dummy data (7 days, 80 jobs/day)
# • Benchmarks live in sidebar
# • Snapshot for Today vs. Yesterday KPIs (wait, cycle, volume)
# • ChatGPT-style UI with memory
# • CSV upload removed                              

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from openai import OpenAI

from knowledge import BEST_PRACTICE
from tone_style import COACH_STYLE
from instruction_set import GUIDELINES, SUGGESTED_PROMPTS
from dummy_data_gen import load_data
from coach_core import get_kpis, handle_simple_prompt

# -------------------------------------------------------------
st.set_page_config(page_title="Ready-Mix Coach",
                   layout="wide",
                   initial_sidebar_state="expanded")

st.image("cdware_logo.png", width=200)
st.title("CDWARE Ready-Mix Coach")

# -------------------------------------------------------------
# 1.  Multi-day dataset in memory
# -------------------------------------------------------------
if "tickets" not in st.session_state:
    st.session_state.tickets = load_data(days_back=7, n_jobs_per_day=80)

raw_df = st.session_state.tickets.copy()
raw_df["start_time"] = pd.to_datetime(raw_df["start_time"], errors="coerce")

kpis = get_kpis(raw_df)

# -------------------------------------------------------------
# 2.  Sidebar  – data preview + benchmarks + quick prompts
# -------------------------------------------------------------
with st.sidebar:
    st.header("Dataset preview")
    if st.checkbox("Show sample rows"):
        st.dataframe(raw_df.head(40), use_container_width=True)

    st.markdown("---")
    st.subheader("🎯 Benchmarks")
    b_util = st.number_input("Util %", 85.0)
    b_m3hr = st.number_input("m³ / HR", 3.5)
    b_m3ld = st.number_input("m³ / Load", 7.6)
    b_wait = st.number_input("Wait min", 19.0)
    b_ot   = st.number_input("OT %", 10.0)
    b_fuel = st.number_input("Fuel $/L", 1.75)

    st.markdown("---")
    with st.expander("💡 Quick questions"):
        for p in SUGGESTED_PROMPTS[:15]:
            if st.button(p, key=f"q_{p}"):
                st.session_state.inject_q = p

bench_line = (
    f"Util {b_util:.1f}% | m³/hr {b_m3hr:.2f} | m³/load {b_m3ld:.2f} | "
    f"Wait {b_wait:.1f} min | OT {b_ot:.1f}% | Fuel ${b_fuel:.2f}/L"
)

# -------------------------------------------------------------
# 3.  KPI snapshots – today / yesterday / 7-day
# -------------------------------------------------------------
wait_today   = kpis["wait_today"]
wait_yest    = kpis["wait_yest"]
cycle_today  = kpis["cycle_today"]
cycle_yest   = kpis["cycle_yest"]
vol_today    = kpis["vol_today"]
vol_yest     = kpis["vol_yest"]
loads_today  = kpis["loads_today"]
loads_yest   = kpis["loads_yest"]

snapshot = (
    f"Today KPIs: wait={wait_today:.1f} min, "
    f"cycle={cycle_today:.1f} min, "
    f"volume={vol_today:.1f} m³, loads={loads_today}\n"
    f"Yesterday KPIs: wait={wait_yest:.1f} min, "
    f"cycle={cycle_yest:.1f} min, "
    f"volume={vol_yest:.1f} m³, loads={loads_yest}\n"
)

# -------------------------------------------------------------
# 4.  Progress expander
# -------------------------------------------------------------
with st.expander("📊 Progress (today vs yesterday)"):
    c1, c2, c3 = st.columns(3)
    c1.metric("Avg wait today",   f"{wait_today:0.1f} min", f"Δ{wait_today - wait_yest:+0.1f}")
    c2.metric("Avg cycle today",  f"{cycle_today:0.1f} min", f"Δ{cycle_today - cycle_yest:+0.1f}")
    c3.metric("Volume today",     f"{vol_today:0.1f} m³", f"Δ{vol_today - vol_yest:+0.1f}")

# -------------------------------------------------------------
# 5.  Chat memory & UI
# -------------------------------------------------------------
if "chat" not in st.session_state:
    st.session_state.chat = []

for item in st.session_state.chat:
    with st.chat_message(item["role"]):
        st.markdown(item["msg"])

def build_prompt(q: str) -> str:
    memory = "\n".join(f"{m['role'].title()}: {m['msg']}" for m in st.session_state.chat[-4:])
    return (
        f"{COACH_STYLE}\n"
        f"{GUIDELINES}\n\n"
        f"{snapshot}"
        f"User benchmarks: {bench_line}\n\n"
        f"{memory}\n\n"
        f"Question: {q}"
    )

def _chat(user_q: str):
    with st.chat_message("user"):
        st.markdown(user_q)

    quick_reply = handle_simple_prompt(user_q, kpis)

    if quick_reply:
        reply = quick_reply
    else:
        with st.spinner("Thinking …"):
            reply = OpenAI().chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": build_prompt(user_q)}]
            ).choices[0].message.content

    with st.chat_message("assistant"):
        st.markdown(reply)

    st.session_state.chat.append({"role": "user", "msg": user_q})
    st.session_state.chat.append({"role": "assistant", "msg": reply})

# allow quick-prompt injection
inject_q = st.session_state.pop("inject_q") if "inject_q" in st.session_state else ""
user_q = st.chat_input("Ask the coach …", placeholder=inject_q or "Ask the coach …")
if user_q:
    _chat(user_q)

# -------------------------------------------------------------
# 6.  Quick chart button
# -------------------------------------------------------------
if st.button("📈 KPI Charts"):
    st.subheader("Average stage durations (7-day)")
    st.bar_chart(raw_df.filter(like="dur_").mean())
