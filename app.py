
import streamlit as st
import pandas as pd
import datetime
import openai
import os
import random
import altair as alt

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
    st.markdown("## 📊 KPI Summary Table")
    df_summary = pd.DataFrame(kpis["summary"]).T.reset_index()
    df_summary.rename(columns={"index": "Period"}, inplace=True)
    st.dataframe(df_summary)

    st.markdown("## 📈 Fleet Productivity")
    chart_data = kpis["df_today"][["truck", "min_prod", "min_total"]].copy()
    chart_data["prod_pct"] = chart_data["min_prod"] / chart_data["min_total"] * 100
    st.altair_chart(
        alt.Chart(chart_data).mark_bar().encode(
            x=alt.X("truck:O", title="Truck ID"),
            y=alt.Y("prod_pct:Q", title="Productivity (%)"),
            tooltip=["truck", "prod_pct"]
        ).properties(height=300),
        use_container_width=True
    )

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
            with st.spinner("Thinking..."):
                try:
                    base_instructions = GUIDELINES["persona"] + "\n\n" + COACH_STYLE["voice"]
                    messages = [{"role": "system", "content": base_instructions}]
                    for m in st.session_state.chat_history:
                        messages.append(m)
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
            st.session_state.chat_history.append({"role": "user", "content": q})
            st.rerun()
