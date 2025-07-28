# app.py
import os
import random

import streamlit as st
import pandas as pd
from openai import OpenAI

from dummy_data_gen import load_data
from coach_core import get_kpis, handle_simple_prompt
from instruction_set import GUIDELINES, SUGGESTED_PROMPTS
from tone_style import COACH_STYLE

# — Require API key up front —
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OpenAI API key not found. Please set OPENAI_API_KEY.")
    st.stop()

client = OpenAI(api_key=api_key)

st.set_page_config(page_title="CDWARE Ready-Mix Coach", layout="wide")
st.markdown(
    """<style>
        #MainMenu, header, footer {visibility: hidden;}
        .block-container {padding-top: 2rem;}
        .stChatFloatingInputContainer {bottom: 3.5rem !important;}
    </style>""",
    unsafe_allow_html=True,
)

# — Load data & compute KPIs —
with st.spinner("Loading ticket data…"):
    df   = load_data(days_back=7, n_jobs_per_day=80)
    kpis = get_kpis(df)

# — Sidebar: choose tab —
st.sidebar.image("https://cdn.cdwtech.ca/logo-white.png", use_container_width=True)
mode = st.sidebar.radio("", ["Reporting", "Chat"])

# — Reporting Tab —
if mode == "Reporting":
    st.header("📊 KPI Summary (Today)")
    cols = st.columns(6)
    metrics = {
        "Loads":           kpis["loads_today"],
        "Utilization %":   f"{kpis['utilization_pct']:.1f}%",
        "Prod. ratio %":   f"{kpis['prod_ratio']:.1f}%",
        "Avg wait (min)":  f"{kpis['avg_wait_min']:.1f}",
        "Trucks":          kpis["n_trucks"],
        "Yesterday loads": kpis["loads_yesterday"],
    }
    for (label, val), col in zip(metrics.items(), cols):
        col.metric(label, val)

    st.subheader("📈 Fleet Productivity by Truck")
    df_t = kpis["df_today"][["truck", "min_prod", "min_total"]].copy()
    if not df_t.empty:
        df_t["prod_pct"] = df_t["min_prod"] / df_t["min_total"] * 100
        st.bar_chart(df_t.set_index("truck")["prod_pct"])
    else:
        st.write("No runs so far today.")

# — Chat Tab —
else:
    st.header("💬 Ask your coach a question")

    if "history" not in st.session_state:
        st.session_state.history = []

    # Render existing chat
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["text"])

    # 1) Allow user to type free-form
    user_q = st.chat_input("Type your question…")
    if user_q:
        st.session_state.history.append({"role": "user", "text": user_q})

        with st.chat_message("assistant"):
            # First try simple rules
            quick = handle_simple_prompt(user_q, kpis)
            if quick:
                ans = quick
            else:
                # Build system prompt from your GUIDELINES & COACH_STYLE
                system_prompt = (
                    f"{GUIDELINES['persona']}\n\n"
                    "Rules:\n" + "\n".join(GUIDELINES["rules"])
                )
                msgs = [{"role": "system",  "content": system_prompt}]
                for m in st.session_state.history:
                    msgs.append({"role": m["role"], "content": m["text"]})

                resp = client.chat.completions.create(
                    model="gpt-4",
                    messages=msgs,
                    temperature=0.4,
                )
                ans = resp.choices[0].message.content.strip()

            st.markdown(ans)
            st.session_state.history.append({"role": "assistant", "text": ans})

    # 2) Suggested questions — handle inline, no rerun()
    st.markdown("### Quick questions:")
    for p in random.sample(SUGGESTED_PROMPTS, k=5):
        if st.button(p):
            st.session_state.history.append({"role": "user", "text": p})
            # immediately compute & display
            with st.chat_message("assistant"):
                quick = handle_simple_prompt(p, kpis)
                if quick:
                    st.markdown(quick)
                    st.session_state.history.append({"role": "assistant", "text": quick})
                else:
                    system_prompt = (
                        f"{GUIDELINES['persona']}\n\n"
                        "Rules:\n" + "\n".join(GUIDELINES["rules"])
                    )
                    msgs = [{"role": "system",  "content": system_prompt}]
                    for m in st.session_state.history:
                        msgs.append({"role": m["role"], "content": m["text"]})

                    resp = client.chat.completions.create(
                        model="gpt-4",
                        messages=msgs,
                        temperature=0.4,
                    )
                    ans = resp.choices[0].message.content.strip()
                    st.markdown(ans)
                    st.session_state.history.append({"role": "assistant", "text": ans})
            break  # only handle one click at a time
