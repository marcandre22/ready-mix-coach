# app.py  –  Ready-Mix Coach  (v3.15)
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
    # 7 days, 80 jobs per day
    st.session_state.tickets = load_data(days_back=7, n_jobs_per_day=80)

raw_df = st.session_state.tickets.copy()
raw_df["start_time"] = pd.to_datetime(raw_df["start_time"], errors="coerce")

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
        for p in SUGGESTED_PROMPTS[:15]:           # first 15 for brevity
            if st.button(p, key=f"q_{p}"):
                st.session_state.inject_q = p      # inject into chat

bench_line = (
    f"Util {b_util:.1f}% | m³/hr {b_m3hr:.2f} | m³/load {b_m3ld:.2f} | "
    f"Wait {b_wait:.1f} min | OT {b_ot:.1f}% | Fuel ${b_fuel:.2f}/L"
)

# -------------------------------------------------------------
# 3.  KPI snapshots – today / yesterday / 7-day
# -------------------------------------------------------------
TODAY, YESTERDAY = datetime.now().date(), datetime.now().date() - timedelta(days=1)
WEEK_START = TODAY - timedelta(days=7)

df_today = raw_df[raw_df.start_time.dt.date == TODAY]
df_yest  = raw_df[raw_df.start_time.dt.date == YESTERDAY]
df_7day  = raw_df[raw_df.start_time.dt.date >= WEEK_START]

def _avg(df, col): return float("nan") if df.empty else df[col].mean()
def _sum(df, col): return float("nan") if df.empty else df[col].sum()

wait_today   = _avg(df_today, "dur_waiting")
wait_yest    = _avg(df_yest , "dur_waiting")
cycle_today  = _avg(df_today, "cycle_time")
cycle_yest   = _avg(df_yest , "cycle_time")
vol_today    = _sum(df_today, "load_volume_m3")
vol_yest     = _sum(df_yest , "load_volume_m3")
loads_today  = len(df_today)
loads_yest   = len(df_yest)

snapshot = (
    f"Today KPIs: wait={wait_today:.1f} min, "
    f"cycle={cycle_today:.1f} min, "
    f"volume={vol_today:.1f} m³, loads={loads_today}\\n"
    f"Yesterday KPIs: wait={wait_yest:.1f} min, "
    f"cycle={cycle_yest:.1f} min, "
    f"volume={vol_yest:.1f} m³, loads={loads_yest}\\n"
)

# -------------------------------------------------------------
# 4.  Progress expander
# -------------------------------------------------------------
with st.expander("📊 Progress (today vs yesterday)"):
    c1, c2, c3 = st.columns(3)
    c1.metric("Avg wait today",   f"{wait_today:0.1f} min",
              f"Δ{wait_today - wait_yest:+0.1f}")
    c2.metric("Avg cycle today",  f"{cycle_today:0.1f} min",
              f"Δ{cycle_today - cycle_yest:+0.1f}")
    c3.metric("Volume today",     f"{vol_today:0.1f} m³",
              f"Δ{vol_today - vol_yest:+0.1f}")

# -------------------------------------------------------------
# 5.  Chat memory & UI
# -------------------------------------------------------------
if "chat" not in st.session_state:
    st.session_state.chat = []        # [{role,msg}]

# show history
for item in st.session_state.chat:
    with st.chat_message(item["role"]):
        st.markdown(item["msg"])

# allow quick-prompt injection
default_q = st.session_state.pop("inject_q", "") if "inject_q" in st.session_state else ""
user_q = st.chat_input("Ask the coach …", placeholder=default_q or "Ask the coach …")

def build_prompt(q: str) -> str:
    memory = "\\n".join(f"{m['role'].title()}: {m['msg']}"
                        for m in st.session_state.chat[-4:])
    return (
        f"{COACH_STYLE}\\n"
        f"{GUIDELINES}\\n\\n"
        f"{snapshot}"
        f"User benchmarks: {bench_line}\\n\\n"
        f"{memory}\\n\\n"
        f"Question: {q}"
    )

if user_q:
    # show user bubble
    with st.chat_message("user"):
        st.markdown(user_q)

    with st.spinner("Thinking …"):
        reply = OpenAI().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": build_prompt(user_q)}]
        ).choices[0].message.content

    with st.chat_message("assistant"):
        st.markdown(reply)

    # save to memory
    st.session_state.chat.append({"role": "user", "msg": user_q})
    st.session_state.chat.append({"role": "assistant", "msg": reply})

# -------------------------------------------------------------
# 6.  Quick chart button
# -------------------------------------------------------------
if st.button("📈 KPI Charts"):
    st.subheader("Average stage durations (7-day)")
    st.bar_chart(raw_df.filter(like="dur_").mean())
