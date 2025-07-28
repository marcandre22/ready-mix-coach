import streamlit as st
import pandas as pd
import os
import random

from openai import OpenAI
from dummy_data_gen import load_data
from coach_core import get_kpis, handle_simple_prompt
from instruction_set import GUIDELINES, SUGGESTED_PROMPTS
from tone_style import COACH_STYLE

# —————— OpenAI client setup ——————
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not client._api_key:
    st.error("Please set OPENAI_API_KEY")
    st.stop()

st.set_page_config(page_title="CDWARE Ready-Mix Coach", layout="wide")

st.markdown(
    """<style>
        #MainMenu, header, footer {visibility: hidden;}
        .block-container {padding-top: 2rem;}
        .stChatFloatingInputContainer {bottom: 3.5rem !important;}
    </style>""",
    unsafe_allow_html=True
)

# —————— Load & score data ——————
with st.spinner("Loading ticket data..."):
    df = load_data(days_back=7, n_jobs_per_day=80)
    kpis = get_kpis(df)

# —————— Sidebar ——————
st.sidebar.image("https://cdn.cdwtech.ca/logo-white.png", use_container_width=True)
tab = st.sidebar.radio("", ["Reporting", "Chat"])

# —————— Reporting view ——————
if tab == "Reporting":
    st.header("📊 KPI Summary (Today)")
    summary = {
        "Loads":            kpis["loads_today"],
        "Total m³":         f"{kpis['total_m3']:.1f}",
        "Avg m³/load":      f"{kpis['avg_m3']:.1f}",
        "Utilization %":    f"{kpis['utilization_pct']:.1f}%",
        "Prod. ratio %":    f"{kpis['prod_ratio']:.1f}%",
        "Avg wait (min)":   f"{kpis['avg_wait_min']:.1f}",
    }
    cols = st.columns(len(summary))
    for (label, val), col in zip(summary.items(), cols):
        col.metric(label, val)

    st.markdown("---")
    st.subheader("📈 Productivity by truck")
    df_t = kpis["df_today"][["truck", "min_prod", "min_total"]].copy()
    if not df_t.empty:
        df_t["prod_pct"] = df_t["min_prod"] / df_t["min_total"] * 100
        st.bar_chart(df_t.set_index("truck")["prod_pct"])
    else:
        st.write("No today’s data to chart.")

# —————— Chat view ——————
else:
    st.header("💬 Ask your coach a question")

    if "history" not in st.session_state:
        st.session_state.history = []

    # Display history
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["text"])

    # User input
    q = st.chat_input("Type your question…")
    if q:
        st.session_state.history.append({"role": "user", "text": q})
        with st.chat_message("assistant"):
            # quick-answer?
            quick = handle_simple_prompt(q, kpis)
            if quick:
                ans = quick
            else:
                # build system prompt
                sys = (
                    f"{GUIDELINES['persona']}\n\n"
                    + "Rules:\n" + "\n".join(GUIDELINES["rules"])
                )
                msgs = [{"role": "system", "content": sys}]
                msgs += [{"role": m["role"], "content": m["text"]} for m in st.session_state.history]

                resp = client.chat.completions.create(
                    model="gpt-4",
                    messages=msgs,
                    temperature=0.4,
                )
                ans = resp.choices[0].message.content.strip()

            st.markdown(ans)
            st.session_state.history.append({"role": "assistant", "text": ans})

    # Suggested quick prompts
    st.markdown("#### Quick questions:")
    for p in random.sample(SUGGESTED_PROMPTS, k=5):
        if st.button(p):
            # inject
            st.session_state.history.append({"role": "user", "text": p})
            st.experimental_rerun()
