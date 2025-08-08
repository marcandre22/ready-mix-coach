# app.py – CDWARE Ready-Mix Coach (tool-calling + filters + coach note)
import json
import random
import pandas as pd
import streamlit as st
from datetime import datetime, date

from openai import OpenAI

from dummy_data_gen import load_data
from coach_core import get_kpis
from instruction_set import GUIDELINES, SUGGESTED_PROMPTS
from tone_style import COACH_STYLE
from prompt_utils import build_system_prompt
from tools import compute_volume, compare_utilization, wait_by_hour

# ----------------------------
# OpenAI client (new SDK style)
# ----------------------------
client = OpenAI()
client_api_key = client.api_key
if not client_api_key:
    st.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
    st.stop()

st.set_page_config(page_title="CDWARE Ready-Mix Coach", layout="wide", initial_sidebar_state="expanded")
st.markdown(
    """
    <style>
      .stChatFloatingInputContainer { bottom: 3.5rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------
# Load deterministic dummy data (seed)
# -----------------------------------
with st.spinner("Loading ticket data..."):
    df_base = load_data(days_back=7, n_jobs_per_day=80, seed=7)
    if "date" not in df_base.columns:
        df_base["date"] = pd.to_datetime(df_base["start_time"]).dt.date

# ----------------
# Sidebar filters
# ----------------
st.sidebar.image("cdware_logo.png", use_container_width=True)
st.sidebar.markdown("### Filters")

plants = sorted(df_base["origin_plant"].unique())
sites = sorted(df_base["job_site"].unique())
drivers = sorted(df_base["driver"].unique())

sel_plants = st.sidebar.multiselect("Plant", plants, default=plants)
sel_sites = st.sidebar.multiselect("Site", sites, default=sites)
sel_drivers = st.sidebar.multiselect("Driver", drivers, default=drivers)

mind, maxd = df_base["date"].min(), df_base["date"].max()
dr_from, dr_to = st.sidebar.date_input("Date range", (mind, maxd))
if isinstance(dr_from, list) or isinstance(dr_to, list):  # Streamlit sometimes returns list
    dr_from, dr_to = dr_from[0], dr_to[0]

mask = (
    df_base["origin_plant"].isin(sel_plants)
    & df_base["job_site"].isin(sel_sites)
    & df_base["driver"].isin(sel_drivers)
    & (df_base["date"] >= dr_from)
    & (df_base["date"] <= dr_to)
)
df = df_base.loc[mask].copy()

# -------------
# Compute KPIs
# -------------
kpis = get_kpis(df)

# ----------------
# Daily coach note
# ----------------
def make_coach_note():
    """Small briefing that uses tool outputs, summarized by the model."""
    try:
        # Gather grounded facts via tools
        facts = {}
        facts["util_compare"] = compare_utilization(kpis, benchmark=85.0)
        facts["wait_by_hour"] = wait_by_hour(kpis["df_today"])
        facts["loads_today"] = int(kpis["loads_today"])
        facts["utilization_pct"] = float(kpis["utilization_pct"])
        facts["prod_ratio"] = float(kpis["prod_ratio"])

        sys = build_system_prompt(GUIDELINES, COACH_STYLE)
        msgs = [
            {"role": "system", "content": sys},
            {"role": "user", "content": (
                "Create a 4-bullet 'Coach Note' for dispatch: "
                "1) today loads/utilization/prod ratio, "
                "2) one driver/plant/site focus from wait_by_hour (if pattern), "
                "3) utilization vs 85% benchmark with delta, "
                "4) a single actionable suggestion.\n\n"
                f"Facts (JSON): {json.dumps(facts)}"
            )},
        ]
        resp = client.chat.completions.create(model="gpt-5-chat", messages=msgs, temperature=0.2)
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Coach note unavailable: {e}"

if "coach_note" not in st.session_state or st.session_state.get("coach_note_key") != (dr_from, dr_to, tuple(sel_plants), tuple(sel_sites), tuple(sel_drivers)):
    st.session_state.coach_note = make_coach_note()
    st.session_state.coach_note_key = (dr_from, dr_to, tuple(sel_plants), tuple(sel_sites), tuple(sel_drivers))

with st.container():
    st.subheader("📓 Coach Note")
    st.success(st.session_state.coach_note)

# ----------------------------
# KPI Snapshot + quick chart
# ----------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Loads (today)", kpis["loads_today"])
c2.metric("Utilization", f"{kpis['utilization_pct']:.1f}%")
c3.metric("Productive time", f"{kpis['prod_ratio']:.1f}%")
c4.metric("Avg wait (min)", f"{kpis['avg_wait_min']:.1f}")

with st.expander("📈 Waiting by hour (today)"):
    series = wait_by_hour(kpis["df_today"])["series"]
    if series:
        dfc = pd.DataFrame(series)
        dfc = dfc.sort_values("hour").set_index("hour")
        st.line_chart(dfc["avg_wait_min"])
    else:
        st.info("No data for selected filters.")

# -----------------
# Debug mode toggle
# -----------------
debug = st.sidebar.checkbox("Debug mode", value=False)
if debug and "debug_log" not in st.session_state:
    st.session_state.debug_log = []

def log_debug(payload):
    if debug:
        st.session_state.debug_log.append(payload)

# --------------------------
# Chat & tool-calling engine
# --------------------------
st.markdown("## 💬 Ask your coach")
if "history" not in st.session_state:
    st.session_state.history = []

for m in st.session_state.history:
    with st.chat_message(m["role"]):
        st.markdown(m["text"])

def tool_call_router(messages):
    """
    Ask the model; if it returns a tool call, execute it and ask for a final answer.
    Returns final text.
    """
    system_prompt = build_system_prompt(GUIDELINES, COACH_STYLE)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "compute_volume",
                "description": "Get delivered volume (m3) for a period.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period": {"type": "string", "enum": ["today", "yesterday"]}
                    },
                    "required": ["period"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "compare_utilization",
                "description": "Compare today utilization vs a benchmark.",
                "parameters": {
                    "type": "object",
                    "properties": {"benchmark": {"type": "number"}},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "wait_by_hour",
                "description": "Average wait minutes for each hour today.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
    ]

    msgs = [{"role": "system", "content": system_prompt}] + messages

    resp = client.chat.completions.create(
        model="gpt-5-chat",
        messages=msgs,
        tools=tools,
        tool_choice="auto",
        temperature=0.2,
    )
    msg = resp.choices[0].message
    log_debug({"stage": "initial", "message": msg})

    if getattr(msg, "tool_calls", None):
        # Execute just the first tool for simplicity; you can loop if you want multi-step
        call = msg.tool_calls[0]
        name = call.function.name
        args = json.loads(call.function.arguments or "{}")

        # Run tool
        if name == "compute_volume":
            result = compute_volume(df, period=args.get("period", "today"))
        elif name == "compare_utilization":
            result = compare_utilization(kpis, float(args.get("benchmark", 85.0)))
        elif name == "wait_by_hour":
            result = wait_by_hour(kpis["df_today"])
        else:
            result = {"ok": False, "error": f"Unknown tool: {name}"}

        log_debug({"stage": "tool_result", "tool": name, "result": result})

        # Send tool result back for the final, natural language answer
        msgs.append({
            "role": "tool",
            "tool_call_id": call.id,
            "name": name,
            "content": json.dumps(result),
        })
        final = client.chat.completions.create(model="gpt-5-chat", messages=msgs, temperature=0.2)
        return final.choices[0].message.content.strip()
    else:
        return msg.content.strip()

user_q = st.chat_input("Ask a question (e.g., 'Compare utilization to 85% benchmark')")
if user_q:
    st.session_state.history.append({"role": "user", "text": user_q})
    with st.chat_message("user"):
        st.markdown(user_q)

    with st.chat_message("assistant"):
        try:
            answer = tool_call_router([{"role": "user", "content": user_q}])
            st.markdown(answer)
            st.session_state.history.append({"role": "assistant", "text": answer})
        except Exception as e:
            st.error(f"There was an error generating a response. {e}")

# -------------------
# Suggested questions
# -------------------
st.markdown("#### Suggested questions:")
cols = st.columns(2)
for i, q in enumerate(SUGGESTED_PROMPTS[:10]):  # show first 10 to keep it compact
    if cols[i % 2].button(q):
        st.session_state.history.append({"role": "user", "text": q})
        st.rerun()

# -------------
# Debug panel
# -------------
if debug:
    with st.expander("🛠 Debug log"):
        st.json(st.session_state.get("debug_log", []))
