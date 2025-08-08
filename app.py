import os
import random
import pandas as pd
import streamlit as st

from dummy_data_gen import load_data
from coach_core import get_kpis, handle_simple_prompt
from instruction_set import GUIDELINES, SUGGESTED_PROMPTS
from tone_style import COACH_STYLE
from prompt_utils import build_system_prompt
from model_utils import chat_call  # <-- model fallback (GPT-5 -> 4o -> 4o-mini)

# -----------------------------
# Environment / basic checks
# -----------------------------
if not os.getenv("OPENAI_API_KEY"):
    st.error("OpenAI API key not found. Please set OPENAI_API_KEY.")
    st.stop()

st.set_page_config(page_title="CDWARE Ready-Mix Coach", layout="wide")
st.markdown("""
    <style>
        #MainMenu, header, footer {visibility: hidden;}
        .block-container {padding-top: 1rem;}
        .stChatFloatingInputContainer {bottom: 3.5rem !important;}
    </style>
""", unsafe_allow_html=True)

# ---------------------------------
# Load data + compute KPIs (cached)
# ---------------------------------
with st.spinner("Loading ticket data..."):
    df = load_data(days_back=7, n_jobs_per_day=80)
    kpis = get_kpis(df)

# ---------------------------------
# Helpers
# ---------------------------------
def process_user_question(user_input: str) -> str:
    """Route to rules first, then LLM with model fallback."""
    # Quick deterministic answers
    simple = handle_simple_prompt(user_input, kpis)
    if simple:
        return simple

    # System prompt built from your instruction_set + tone_style
    system_prompt = build_system_prompt(GUIDELINES, COACH_STYLE)

    # Chat history from session
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history]

    # Call LLM with fallback chain (tries GPT-5 first if you set it)
    model_used, text = chat_call(
        messages=[{"role": "system", "content": system_prompt}] + history + [
            {"role": "user", "content": user_input}
        ],
        temperature=0.3,
    )
    # Tag the model used (optional debug)
    return f"_model: {model_used}_\n\n{text}"

# -----------------------------
# Sidebar: nav + (optional) debug
# -----------------------------
st.sidebar.image("https://cdn.cdwtech.ca/logo-white.png", use_container_width=True)
selected_tab = st.sidebar.radio("", ["Reporting", "Chat"], index=0)

with st.sidebar.expander("⚙️ Advanced"):
    st.caption("Set `OPENAI_MODEL` to try a model first (falls back if missing).")
    st.code("OPENAI_MODEL=gpt-5-chat", language="bash")
    debug = st.checkbox("Show debug info", value=False)

# -----------------------------
# Reporting tab
# -----------------------------
if selected_tab == "Reporting":
    st.markdown("## 📊 Reporting Dashboard")

    # Top KPI tiles
    c1, c2, c3 = st.columns(3)
    c1.metric("# Loads (today)", f"{kpis['loads_today']}")
    avg_wait = kpis.get("avg_wait_min")
    c2.metric("Avg Waiting (min)", f"{avg_wait:.1f}" if pd.notna(avg_wait) else "–")
    c3.metric("Utilization", f"{kpis['utilization_pct']:.1f}%"
             if pd.notna(kpis['utilization_pct']) else "–")

    # KPI Summary (today-only, safe keys)
    st.subheader("KPI Summary (Today)")
    df_summary = pd.DataFrame([{
        "loads_today": kpis["loads_today"],
        "loads_yesterday": kpis.get("loads_yesterday", float("nan")),
        "avg_wait_min": kpis.get("avg_wait_min", float("nan")),
        "utilization_pct": kpis.get("utilization_pct", float("nan")),
        "prod_ratio_pct": kpis.get("prod_ratio", float("nan")),
        "prod_min_total": kpis.get("prod_prod_min", float("nan")),
        "idle_min_total": kpis.get("prod_idle_min", float("nan")),
        "n_trucks": kpis.get("n_trucks", 0),
    }]).T.rename(columns={0: "value"})
    st.dataframe(df_summary, use_container_width=True)

    # Fleet Productivity chart (per-truck)
    st.subheader("📈 Fleet Productivity (per truck, today)")
    df_today = kpis["df_today"].copy()
    if not df_today.empty and {"min_prod", "min_total"}.issubset(df_today.columns):
        df_today["prod_pct"] = df_today["min_prod"] / df_today["min_total"] * 100
        chart_df = df_today[["truck", "prod_pct"]].dropna().sort_values("prod_pct", ascending=False)
        chart_df = chart_df.set_index("truck")
        st.bar_chart(chart_df, use_container_width=True)
    else:
        st.info("No productivity data available for today.")

    if debug:
        st.write("**DEBUG:kpis**", kpis)

# -----------------------------
# Chat tab
# -----------------------------
if selected_tab == "Chat":
    st.markdown("## 💬 Ask your coach a question")

    # Chat state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Render history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggested prompts (random 5) — clicking will auto-send the question
    st.markdown("#### Suggested questions:")
    cols = st.columns(1)
    suggestions = random.sample(SUGGESTED_PROMPTS, k=min(5, len(SUGGESTED_PROMPTS)))
    for q in suggestions:
        if st.button(q, use_container_width=True):
            st.session_state.inject_q = q
            st.rerun()

    # Chat input
    user_input = st.chat_input("Ask a question")
    pending_q = st.session_state.pop("inject_q", None)

    question = user_input or pending_q
    if question:
        # User bubble
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Assistant bubble
        with st.chat_message("assistant"):
            try:
                reply = process_user_question(question)
                st.markdown(reply)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error(f"Coach note unavailable: {e}")
        st.rerun()
