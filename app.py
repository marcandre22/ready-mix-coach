import os
import random
import pandas as pd
import streamlit as st

from dummy_data_gen import load_data
from coach_core import get_kpis, handle_simple_prompt
from instruction_set import GUIDELINES, SUGGESTED_PROMPTS
from tone_style import COACH_STYLE
from prompt_utils import build_system_prompt
from model_utils import chat_call  # GPT-5 -> 4o -> 4o-mini fallback


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
        .suggestion-btn button {text-align: left;}
    </style>
""", unsafe_allow_html=True)


# ---------------------------------
# Load data + compute KPIs (cached)
# ---------------------------------
@st.cache_data(show_spinner=False)
def _load_all():
    df_ = load_data(days_back=7, n_jobs_per_day=80)
    k_ = get_kpis(df_)
    return df_, k_

with st.spinner("Loading ticket data..."):
    df, kpis = _load_all()


# ---------------------------------
# LLM helpers
# ---------------------------------
def build_data_context(k: dict) -> str:
    """Compact snapshot the model can rely on."""
    def fmt(x):
        return "–" if x is None or pd.isna(x) else f"{x:.1f}" if isinstance(x, (float, int)) else str(x)

    lines = [
        "DATA SNAPSHOT (today)",
        f"- Loads today: {k.get('loads_today', 0)}",
        f"- Loads yesterday: {k.get('loads_yesterday', 0)}",
        f"- Avg wait (min): {fmt(k.get('avg_wait_min'))}",
        f"- Utilization (%): {fmt(k.get('utilization_pct'))}",
        f"- Productivity ratio (%): {fmt(k.get('prod_ratio'))}",
        f"- Productive minutes: {fmt(k.get('prod_prod_min'))}",
        f"- Idle minutes: {fmt(k.get('prod_idle_min'))}",
        f"- Active trucks: {k.get('n_trucks', 0)}",
        f"- Fuel used today (L): {fmt(k.get('fuel_L_today'))}",
        f"- Distance today (km): {fmt(k.get('distance_km_today'))}",
        f"- Volume today (m³): {fmt(k.get('m3_today'))}",
    ]
    return "\n".join(lines)


def process_user_question(user_input: str) -> str:
    """Route to rules first, then LLM with model fallback and data context."""
    # Quick deterministic answers
    simple = handle_simple_prompt(user_input, kpis)
    if simple:
        return simple

    # Prompts
    system_prompt = build_system_prompt(GUIDELINES, COACH_STYLE)
    data_context = build_data_context(kpis)

    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history]

    model_used, text = chat_call(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": data_context},
            *history,
            {"role": "user", "content": user_input},
        ],
        temperature=0.3,
    )
    # Tag the model used (optional)
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

    c1, c2, c3 = st.columns(3)
    c1.metric("# Loads (today)", f"{kpis['loads_today']}")
    avg_wait = kpis.get("avg_wait_min")
    c2.metric("Avg Waiting (min)", f"{avg_wait:.1f}" if pd.notna(avg_wait) else "–")
    util = kpis.get("utilization_pct")
    c3.metric("Utilization", f"{util:.1f}%" if pd.notna(util) else "–")

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
        "fuel_L_today": kpis.get("fuel_L_today", float("nan")),
        "distance_km_today": kpis.get("distance_km_today", float("nan")),
        "m3_today": kpis.get("m3_today", float("nan")),
    }]).T.rename(columns={0: "value"})
    st.dataframe(df_summary, use_container_width=True)

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

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # --- helper: send a suggestion immediately
    def send_suggestion(q: str):
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        st.session_state.chat_history.append({"role": "user", "content": q})
        try:
            reply = process_user_question(q)
        except Exception as e:
            reply = f"Coach note unavailable: {e}"
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()

    # Render existing history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggested questions – now actually send on click
    st.markdown("#### Suggested questions:")
    suggestions = random.sample(SUGGESTED_PROMPTS, k=min(5, len(SUGGESTED_PROMPTS)))
    for i, q in enumerate(suggestions):
        st.button(q, key=f"sug_{i}", use_container_width=True, on_click=send_suggestion, args=(q,), help="Click to ask this")

    # Freeform input
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
                st.error(f"Coach note unavailable: {e}")
        st.rerun()
