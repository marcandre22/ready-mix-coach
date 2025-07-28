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

# ✅ Set OpenAI API key
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

# Load data
with st.spinner("Loading ticket data..."):
    df = load_data()
    kpis = get_kpis(df)

# Sidebar (Navigation and Filters)
st.sidebar.image("https://cdn.cdwtech.ca/logo-white.png", use_container_width=True)
selected_tab = st.sidebar.radio("", ["Reporting", "Chat"], index=0)

if selected_tab == "Reporting":
    st.markdown("## 🚧 Reporting Dashboard")

    # Top KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("# Loads (vs Yesterday)", f"{kpis['loads_today']}")
    col2.metric("Avg Waiting Time (min)", f"{kpis['prod_idle_min'] / kpis['n_trucks']:.1f}")
    col3.metric("Utilization", f"{kpis['utilization_pct']:.1f}%")

    # Sample Charts (Fleet Productivity)
    import altair as alt
    st.subheader("📈 Fleet Productivity")
    chart_data = kpis["df_today"][["truck", "min_prod", "min_total"]].copy()
    chart_data = chart_data[chart_data["min_total"] > 0]
    chart_data["prod_pct"] = chart_data["min_prod"] / chart_data["min_total"] * 100
    st.altair_chart(
        alt.Chart(chart_data).mark_bar().encode(
            x="truck:O",
            y=alt.Y("prod_pct:Q", scale=alt.Scale(domain=[0, 100])),
            tooltip=["truck", "prod_pct"]
        ).properties(height=300),
        use_container_width=True
    )

elif selected_tab == "Chat":
    st.markdown("## 💬 Ask your coach a question")

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display messages
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input box
    user_input = st.chat_input("Ask a question")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
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

    # Suggested prompts (random 5)
    st.markdown("#### Suggested questions:")
    for q in random.sample(SUGGESTED_PROMPTS, k=min(5, len(SUGGESTED_PROMPTS))):
        if st.button(q):
            st.session_state.chat_history.append({"role": "user", "content": q})
            with st.chat_message("user"):
                st.markdown(q)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
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