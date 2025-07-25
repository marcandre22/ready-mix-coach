# Ready‑Mix Coach – CDWARE (v3.15)
#  ✦ Removes CSV upload
#  ✦ Ensures multi‑day dummy data (7‑day window)
#  ✦ Injects Yesterday KPI snapshot so coach can compare immediately
#  ✦ ChatGPT‑style interface retained

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from openai import OpenAI

from knowledge import BEST_PRACTICE
from tone_style import COACH_STYLE
from instruction_set import GUIDELINES
from dummy_data_gen import load_data

st.set_page_config(page_title="Ready‑Mix Coach", layout="wide", initial_sidebar_state="expanded")

st.image("cdware_logo.png", width=200)
st.title("CDWARE Ready‑Mix Coach")

# ------------------------------------------------------------------
# 1. Load multi‑day simulated data (7 days, 80 tickets / day)
# ------------------------------------------------------------------
if "tickets" not in st.session_state:
    st.session_state.tickets = load_data(days_back=7, n_jobs_per_day=80)

raw_df = st.session_state.tickets.copy()
raw_df["start_time"] = pd.to_datetime(raw_df["start_time"], errors="coerce")

# ------------------------------------------------------------------
# 2. Sidebar tools & Benchmarks
# ------------------------------------------------------------------
with st.sidebar:
    st.header("Dataset preview")
    if st.checkbox("Show sample rows"):
        st.dataframe(raw_df.head(40), use_container_width=True)

    st.markdown("---")
    st.subheader("🎯 Benchmarks")
    b_util  = st.number_input("Util %", 85.0)
    b_m3hr  = st.number_input("m³ / HR", 3.5)
    b_m3ld  = st.number_input("m³ / Load", 7.6)
    b_wait  = st.number_input("Wait min", 19.0)
    b_ot    = st.number_input("OT %", 10.0)
    b_fuel  = st.number_input("Fuel $/L", 1.75)

bench_line = (
    f"Util {b_util:.1f}% | m³/hr {b_m3hr:.2f} | m³/load {b_m3ld:.2f} | "
    f"Wait {b_wait:.1f} min | OT {b_ot:.1f}% | Fuel ${b_fuel:.2f}/L"
)

# ------------------------------------------------------------------
# 3. KPI helper functions
# ------------------------------------------------------------------
TODAY      = datetime.now().date()
YESTERDAY  = TODAY - timedelta(days=1)
WEEK_START = TODAY - timedelta(days=7)

df_today   = raw_df[raw_df.start_time.dt.date == TODAY]
df_yest    = raw_df[raw_df.start_time.dt.date == YESTERDAY]
df_7       = raw_df[raw_df.start_time.dt.date >= WEEK_START]

def _avg(df, col):
    return float('nan') if df.empty else df[col].mean()

# pre‑compute deltas so coach sees them
wait_today  = _avg(df_today, 'dur_waiting')
wait_yest   = _avg(df_yest,  'dur_waiting')
cycle_today = _avg(df_today, 'cycle_time')
cycle_yest  = _avg(df_yest,  'cycle_time')

# ------------------------------------------------------------------
# 4. Progress quick view
# ------------------------------------------------------------------
with st.expander("📊 Progress (today vs yesterday)"):
    c1, c2 = st.columns(2)
    c1.metric("Avg wait today",  f"{wait_today:0.1f} min",  f"Δ{wait_today - wait_yest:+0.1f}")
    c2.metric("Avg cycle today", f"{cycle_today:0.1f} min", f"Δ{cycle_today - cycle_yest:+0.1f}")

# ------------------------------------------------------------------
# 5. Chat memory + UI
# ------------------------------------------------------------------
if "chat" not in st.session_state:
    st.session_state.chat = []  # {role,msg}

for item in st.session_state.chat:
    with st.chat_message(item['role']):
        st.markdown(item['msg'])

# Build snapshot strings once per run
snapshot = (
    f"Today KPIs: wait_avg={wait_today:0.1f} min, cycle_avg={cycle_today:0.1f} min\n"
    f"Yesterday KPIs: wait_avg={wait_yest:0.1f} min, cycle_avg={cycle_yest:0.1f} min\n"
)

def build_prompt(question: str) -> str:
    memory = "\n".join(f"{m['role'].title()}: {m['msg']}" for m in st.session_state.chat[-4:])
    return (
        f"You are a seasoned ready‑mix dispatch coach.\n\n"
        f"{memory}\n\n"
        f"{snapshot}"
        f"User benchmarks: {bench_line}\n\n"
        f"Best practices: {BEST_PRACTICE}\nTone: {COACH_STYLE}\nInstructions: {GUIDELINES}\n\n"
        f"Question: {question}"
    )

# ------------------------------------------------------------------
# 6. Chat input & response
# ------------------------------------------------------------------
user_q = st.chat_input("Ask the coach …")
if user_q:
    with st.chat_message("user"):
        st.markdown(user_q)

    with st.spinner("Thinking …"):
        reply = OpenAI().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content": build_prompt(user_q)}]
        ).choices[0].message.content

    with st.chat_message("assistant"):
        st.markdown(reply)

    st.session_state.chat.append({"role":"user", "msg":user_q})
    st.session_state.chat.append({"role":"assistant", "msg":reply})

# ------------------------------------------------------------------
# 7. Quick KPI chart button
# ------------------------------------------------------------------
if st.button("📈 KPI Charts"):
    st.subheader("Average stage durations (7‑day average)")
    st.bar_chart(raw_df.filter(like="dur_").mean())
