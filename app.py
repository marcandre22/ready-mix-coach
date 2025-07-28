
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

def process_user_question(user_input):
    simple = handle_simple_prompt(user_input, kpis)
    if simple:
        return simple

    system_prompt = f"{GUIDELINES['persona']}

Rules:
" + "\n".join(GUIDELINES["rules"])
    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history]

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()

st.sidebar.image("https://cdn.cdwtech.ca/logo-white.png", use_container_width=True)
selected_tab = st.sidebar.radio("", ["Reporting", "Chat"], index=0)

if selected_tab == "Reporting":
    st.markdown("## 📊 KPI Summary Table")
    df_summary = pd.DataFrame([{
        "Period": "daily",
        "loads": kpis["loads_today"],
        "m3": kpis.get("total_m3", 0),
        "avg_m3": kpis.get("avg_m3", 0),
        "utilization": kpis["utilization_pct"],
        "prod_ratio": kpis["prod_ratio"],
        "idle_min": kpis["prod_idle_min"],
        "prod_min": kpis["prod_prod_min"],
        "n_trucks": kpis["n_trucks"]
    }])
    df_summary.set_index("Period", inplace=True)
    st.dataframe(df_summary)

    import altair as alt
    st.markdown("## 📈 Fleet Productivity")
    chart_data = kpis["df_today"][["truck", "min_prod", "min_total"]].copy()
    chart_data["prod_pct"] = chart_data["min_prod"] / chart_data["min_total"] * 100
    chart = alt.Chart(chart_data).mark_bar().encode(
        x="truck:O",
        y="prod_pct:Q",
        tooltip=["truck", "prod_pct"]
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

elif selected_tab == "Chat":
    st.markdown("## 💬 Ask your coach a question")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask a question")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            try:
                reply = process_user_question(user_input)
                st.markdown(reply)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error("There was an error generating a response. Please try again later.")

    st.markdown("#### Suggested questions:")
    for q in random.sample(SUGGESTED_PROMPTS, k=min(5, len(SUGGESTED_PROMPTS))):
        if st.button(q):
            st.session_state.chat_history.append({"role": "user", "content": q})
            st.rerun()
