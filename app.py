import streamlit as st
import pandas as pd
import datetime
import openai
import random

from dummy_data_gen import load_data
from coach_core import get_kpis, handle_simple_prompt
from instruction_set import GUIDELINES, SUGGESTED_PROMPTS
from tone_style import COACH_STYLE

# --- UI Config ---
st.set_page_config(page_title="CDWARE Ready-Mix Coach", layout="wide")
st.markdown("<h1 style='margin-bottom: 0'>🧠 Ask your coach a question</h1>", unsafe_allow_html=True)

# --- Load Data + KPIs ---
df = load_data(days_back=3)
kpis = get_kpis(df, op_minutes=600)

# --- Suggested Prompts ---
st.markdown("### Suggested questions:")
for p in random.sample(SUGGESTED_PROMPTS, k=5):
    if st.button(p):
        st.session_state["last_prompt"] = p
        st.rerun()

# --- Input Box ---
prompt = st.chat_input("Ask a question")
if prompt:
    st.session_state["last_prompt"] = prompt
    st.rerun()

prompt = st.session_state.get("last_prompt", "")
if prompt:
    st.markdown(f"**{prompt}**")

    # 1. Check rule-based answer
    reply = handle_simple_prompt(prompt, kpis)

    # 2. Fallback to OpenAI
    if not reply:
        openai.api_key = st.secrets.get("OPENAI_API_KEY")
        messages = [
            {"role": "system", "content": GUIDELINES + "\n\n" + COACH_STYLE},
            {"role": "user", "content": prompt},
        ]
        with st.spinner("Thinking..."):
            try:
                res = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=messages,
                    temperature=0.4
                )
                reply = res.choices[0].message.content
            except Exception as e:
                reply = f"⚠️ OpenAI error: {e}"

    st.success(reply)
