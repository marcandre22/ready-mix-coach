import streamlit as st
import pandas as pd
import openai, os, random

from dummy_data_gen import load_data
from coach_core     import get_kpis, handle_simple_prompt
from instruction_set import GUIDELINES, SUGGESTED_PROMPTS
from tone_style     import COACH_STYLE

# — API key —
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    st.error("Missing OPENAI_API_KEY")
    st.stop()

# — Page config & styles —
st.set_page_config(page_title="CDWARE Ready-Mix Coach", layout="wide")
st.markdown("""
<style>
  #MainMenu, header, footer {visibility: hidden;}
  .block-container {padding-top:2rem;}
  .stChatFloatingInputContainer {bottom:3.5rem!important;}
</style>
""", unsafe_allow_html=True)

# — Load & compute KPIs —
with st.spinner("Loading ticket data…"):
    df   = load_data(days_back=7, n_jobs_per_day=80)
    kpis = get_kpis(df)

# — Process user question (simple → GPT) —
def process_user_question(text: str) -> str:
    # 1) fast path
    simple = handle_simple_prompt(text, kpis)
    if simple is not None:
        return simple

    # 2) compose system prompt
    sys_parts = [ GUIDELINES["persona"] ]
    sys_parts += [ "Rules:" ] + [ f"- {r}" for r in GUIDELINES["rules"] ]
    sys_parts += [ "\nAvoid:" ] + [ f"- {a}" for a in COACH_STYLE.get("avoid",[]) ]
    sys_parts += [ f"\nClosing: {COACH_STYLE.get('closing','')}" ]
    system_prompt = "\n".join(sys_parts)

    # 3) assemble messages
    msgs = [{"role":"system","content":system_prompt}]
    msgs += st.session_state.get("chat_history", [])

    msgs.append({"role":"user","content":text})
    reply = openai.ChatCompletion.create(
        model="gpt-4",
        messages=msgs,
        temperature=0.4,
    ).choices[0].message.content.strip()
    return reply

# — Sidebar navigation —
st.sidebar.image("https://cdn.cdwtech.ca/logo-white.png", use_container_width=True)
tab = st.sidebar.radio("", ["Reporting","Chat"])

# — Reporting tab —
if tab == "Reporting":
    st.subheader("🚧 Reporting Dashboard")
    # KPI summary
    df_sum = pd.DataFrame([{
        "Period": "today",
        "Loads": kpis["loads_today"],
        "Total m³": kpis["total_m3"],
        "Avg m³/Load": kpis["avg_m3"],
        "Util %": kpis["utilization_pct"],
        "Idle min": kpis["idle_min"],
        "Prod min": kpis["prod_min"],
        "Trucks": kpis["n_trucks"],
    }]).set_index("Period")
    st.dataframe(df_sum, use_container_width=True)

    # Fleet productivity chart
    st.subheader("📈 Fleet Productivity (today)")
    dfp = kpis["df_today"].copy()
    if not dfp.empty:
        dfp["prod_pct"] = dfp["cycle_time"] / (dfp["cycle_time"] + dfp["dur_waiting"]) * 100
        import altair as alt
        chart = (
            alt.Chart(dfp)
            .mark_bar()
            .encode(
                x="truck:O",
                y=alt.Y("prod_pct:Q", scale=alt.Scale(domain=[0,100])),
                tooltip=["truck","prod_pct"]
            )
            .properties(height=300)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("No data for today’s productivity.")

# — Chat tab —
else:
    st.subheader("💬 Ask your coach a question")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # render history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # user input
    q = st.chat_input("Ask a question…")
    if q:
        # append user and assistant
        st.session_state.chat_history.append({"role":"user","content":q})
        with st.chat_message("user"):
            st.markdown(q)

        with st.chat_message("assistant"):
            ans = process_user_question(q)
            st.markdown(ans)
            st.session_state.chat_history.append({"role":"assistant","content":ans})

    # suggested prompts
    st.markdown("#### Suggested questions:")
    for s in SUGGESTED_PROMPTS:
        if st.button(s):
            # inject and rerun to trigger same path as manual input
            st.session_state.chat_history.append({"role":"user","content":s})
            st.experimental_rerun()
