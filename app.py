# app.py – updated with pending prompt logic and safe summary rendering

import streamlit as st
import pandas as pd
import datetime
import openai
import os
import random

from dummy_data_gen import load_data
from coach_core import get_kpis, handle_simple_prompt
from instruction_set import GUIDELINES, SUGGESTED_PROMPTS
from tone_style import COACH_STYLE

openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    st.error("OpenAI API key not found. Please set OPENAI_API_KEY.")
    st.stop()

st.set_page_config(page_title="CDWARE Ready-Mix Coach", layout="wide")
st.markdown("""
    <style>
        #MainMenu, header, footer {visibility: hidden;}
        .block-container {padding-top: 2rem;}
        .stChatFloatingInputContainer {bottom: 3.5rem !important;}
    </style>
""", unsafe_allow_html=True)

with st.spinner("Loading ticket data..."):
    df = load_data()
    kpis = get_kpis(df)

st.sidebar.image("https://cdn.cdwtech.ca/logo-white.png", use_container_width=True)
selected_tab = st.sidebar.radio("", ["Reporting", "Chat"], index=0)

if selected_tab == "Reporting":
    st.markdown("## 🚧 Reporting Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("# Loads", f"{kpis['summary']['loads']}")
    col2.metric("Avg Waiting Time (min)", f"{kpis['summary']['idle_min'] / kpis['summary']['n_trucks']:.1f}")
    col3.metric("Utilization", f"{kpis['summary']['utilization']:.1f}%")

    st.subheader("📊 KPI Summary Table")
    df_summary = pd.DataFrame([kpis["summary"]])
    st.dataframe(df_summary)

elif selected_tab == "Chat":
    st.markdown("## 💬 Ask your coach a question")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Inject clicked suggestion if available
    if "pending_prompt" in st.session_state:
        user_input = st.session_state.pop("pending_prompt")
    else:
        user_input = st.chat_input("Ask a question")

    # Display previous messages
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                coach_answer = handle_simple_prompt(user_input, kpis)
                if coach_answer:
                    st.markdown(coach_answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": coach_answer})
                else:
                    try:
                        messages = [{"role": "system", "content": COACH_STYLE}] + st.session_state.chat_history
                        response = openai.ChatCompletion.create(
                            model="gpt-4",
                            messages=messages,
                            temperature=0.4,
                        )
                        answer = response.choices[0].message.content.strip()
                        st.markdown(answer)
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    except Exception as e:
                        st.error("There was an error generating a response. Please try again later.")

    st.markdown("#### Suggested questions:")
    for q in random.sample(SUGGESTED_PROMPTS, k=min(5, len(SUGGESTED_PROMPTS))):
        if st.button(q):
            st.session_state.pending_prompt = q
            st.rerun()