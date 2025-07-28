import streamlit as st
import pandas as pd
import openai
import os
import random

from dummy_data_gen import load_data
from coach_core import get_kpis, handle_simple_prompt
from instruction_set import GUIDELINES, SUGGESTED_PROMPTS
from tone_style import COACH_STYLE

# Set OpenAI API key
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

# Sidebar
st.sidebar.image("https://cdn.cdwtech.ca/logo-white.png", use_container_width=True)
selected_tab = st.sidebar.radio("", ["Reporting", "Chat"], index=0)

# Reporting
if selected_tab == "Reporting":
    st.markdown("## 🚧 Reporting Dashboard")

    # Top KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("# Loads (vs Yesterday)", f"{kpis.get('loads_today', 0)}")
    col2.metric("Avg Waiting Time (min)", f"{kpis.get('prod_idle_min', 0) / max(kpis.get('n_trucks', 1),1):.1f}")
    col3.metric("Utilization", f"{kpis.get('utilization_pct', 0):.1f}%")

    # Summary Table
    if "summary" in kpis and isinstance(kpis["summary"], dict):
        st.subheader("📊 KPI Summary Table")
        df_summary = pd.DataFrame(kpis["summary"]).T
        df_summary.index.name = "Period"
        st.dataframe(df_summary)

    # Productivity Chart
    import altair as alt
    st.subheader("📈 Fleet Productivity")
    df_today = kpis.get("df_today", pd.DataFrame())
    if not df_today.empty:
        chart_data = df_today[["truck", "min_prod", "min_total"]].copy()
        chart_data["prod_pct"] = chart_data["min_prod"] / chart_data["min_total"] * 100
        st.altair_chart(
            alt.Chart(chart_data).mark_bar().encode(
                x="truck:O", y="prod_pct:Q", tooltip=["truck", "prod_pct"]
            ).properties(height=300),
            use_container_width=True
        )

# Chat
elif selected_tab == "Chat":
    st.markdown("## 💬 Ask your coach a question")

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display past conversation
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Prompt input
    user_input = st.chat_input("Ask a question")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Try quick handle, else send to GPT
        response = handle_simple_prompt(user_input, kpis)
        with st.chat_message("assistant"):
            try:
                if response:
                    st.markdown(response)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                else:
                    # Generate response from OpenAI
                    context = {
                        "role": "system",
                        "content": GUIDELINES["persona"] + "\n\n" + COACH_STYLE["voice"]
                    }
                    messages = [context] + st.session_state.chat_history
                    result = openai.ChatCompletion.create(
                        model="gpt-4",
                        messages=messages,
                        temperature=0.4
                    )
                    reply = result.choices[0].message.content.strip()
                    st.markdown(reply)
                    st.session_state.chat_history.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error("There was an error generating a response. Please try again later.")

    # Show suggestions if no user input
    if not user_input:
        st.markdown("#### Suggested questions:")
        for q in random.sample(SUGGESTED_PROMPTS, k=min(5, len(SUGGESTED_PROMPTS))):
            if st.button(q):
                st.session_state.chat_history.append({"role": "user", "content": q})
                st.rerun()
