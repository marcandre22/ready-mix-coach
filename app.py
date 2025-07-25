# Ready‑Mix Coach – CDWARE (v3.14)
# ➤ Multi‑day dummy data
# ➤ Benchmarks moved to sidebar
# ➤ ChatGPT‑style interface using st.chat_input / st.chat_message

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from openai import OpenAI

from knowledge import BEST_PRACTICE
from tone_style import COACH_STYLE
from instruction_set import GUIDELINES
from dummy_data_gen import load_data

st.set_page_config(page_title="Ready‑Mix Coach", layout="wide", initial_sidebar_state="expanded")

# ---- Header ------------------------------------------------------
st.image("cdware_logo.png", width=200)
st.title("CDWARE Ready‑Mix Coach")

# ---- Data --------------------------------------------------------
if "tickets" not in st.session_state:
    st.session_state.tickets = load_data(days_back=7, n_jobs_per_day=80)

# CSV uploader
with st.sidebar.expander("📤 Upload additional tickets (CSV)"):
    up = st.file_uploader("Choose CSV", type=["csv"])
    if up is not None:
        df_new = pd.read_csv(up)
        if "start_time" in df_new.columns:
            df_new["start_time"] = pd.to_datetime(df_new["start_time"], errors="coerce")
        st.session_state.tickets = pd.concat([st.session_state.tickets, df_new], ignore_index=True)
        st.success(f"Added {len(df_new)} rows — dataset now {len(st.session_state.tickets)} rows")

raw_df = st.session_state.tickets.copy()
raw_df["start_time"] = pd.to_datetime(raw_df["start_time"], errors="coerce")

# ---- Sidebar: dataset + benchmarks ------------------------------
st.sidebar.header("🔎 Dataset tools")
if st.sidebar.checkbox("Preview table"):
    st.dataframe(raw_df.head(40), use_container_width=True)
if st.sidebar.button("Download CSV"):
    st.sidebar.download_button("get_ready_mix.csv", raw_df.to_csv(index=False))

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Benchmarks")
bench_util  = st.sidebar.number_input("Utilization %", 85.0)
bench_m3hr  = st.sidebar.number_input("m³ / HR", 3.5)
bench_m3ld  = st.sidebar.number_input("m³ / Load", 7.6)
bench_wait  = st.sidebar.number_input("Wait min", 19.0)
bench_ot    = st.sidebar.number_input("OT %", 10.0)
bench_fuel  = st.sidebar.number_input("Fuel $/L", 1.75)

bench_txt = (
    f"Util {bench_util:.1f}% | m³/hr {bench_m3hr:.2f} | m³/load {bench_m3ld:.2f} | "
    f"Wait {bench_wait:.1f} min | OT {bench_ot:.1f}% | Fuel ${bench_fuel:.2f}/L"
)

# ---- Progress quick‑view ----------------------------------------
with st.expander("📊 Progress (today vs yesterday vs 7‑day)"):
    today,d1w = datetime.now().date(), datetime.now().date()-timedelta(days=1)
    d7 = today - timedelta(days=7)
    dfT = raw_df[raw_df.start_time.dt.date==today]
    dfY = raw_df[raw_df.start_time.dt.date==d1w]
    df7 = raw_df[raw_df.start_time.dt.date>=d7]
    def avg(col,frame):
        return frame[col].mean() if not frame.empty else float('nan')
    waitT,waitY,wait7 = avg('dur_waiting',dfT), avg('dur_waiting',dfY), avg('dur_waiting',df7)
    utilT,utilY = len(dfT)/(len(raw_df)+1e-9)*100, len(dfY)/(len(raw_df)+1e-9)*100
    c1,c2 = st.columns(2)
    c1.metric("Avg wait today", f"{waitT:0.1f} min", f"Δ{waitT-waitY:+0.1f}")
    c1.metric("Avg wait 7‑day", f"{wait7:0.1f} min")
    c2.metric("Util today", f"{utilT:0.1f}%", f"Δ{utilT-utilY:+0.1f}")

# ---- Chat memory -------------------------------------------------
if "chat" not in st.session_state:
    st.session_state.chat = []  # list[dict(role,msg)]

def show_history():
    for item in st.session_state.chat:
        with st.chat_message(item['role']):
            st.markdown(item['msg'])

show_history()

# ---- Chat input --------------------------------------------------
user_q = st.chat_input("Ask the coach…")
if user_q:
    with st.chat_message("user"):
        st.markdown(user_q)

    def build_prompt(q):
        kpi_wait = raw_df['dur_waiting'].mean()
        kpi_cycle = raw_df['cycle_time'].mean()
        memory = "\n".join(f"{m['role'].title()}: {m['msg']}" for m in st.session_state.chat[-4:])
        return (
            f"You are a senior ready‑mix dispatch coach.\n{memory}\n\n"
            f"KPIs: wait_avg={kpi_wait:.1f} min, cycle_avg={kpi_cycle:.1f} min\n"
            f"User benchmarks: {bench_txt}\n"
            f"Best practices: {BEST_PRACTICE}\nTone: {COACH_STYLE}\nInstructions: {GUIDELINES}\n"
            f"Question: {q}"
        )

    with st.spinner("Thinking…"):
        client = OpenAI()
        coach_reply = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content": build_prompt(user_q)}]
        ).choices[0].message.content

    with st.chat_message("assistant"):
        st.markdown(coach_reply)

    st.session_state.chat.append({"role":"user","msg":user_q})
    st.session_state.chat.append({"role":"assistant","msg":coach_reply})

# ---- Quick KPI chart --------------------------------------------
if st.button("📈 KPI Charts"):
    st.subheader("Average stage durations (min)")
    st.bar_chart(raw_df.filter(like="dur_").mean())
