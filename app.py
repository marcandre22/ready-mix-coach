# app.py – CDWARE Ready-Mix Coach (tool-calling + filters + coach note + many tools)
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

# NEW: large tool suite
from tools import (
    compute_volume,
    compare_utilization,
    wait_by_hour,
    fuel_cost_today,
    co2_from_fuel_today,
    driver_efficiency_today,
    top_wait_jobs_48h,
    top_water_added_week,
    cycle_by_plant,
    distance_over_km,
    success_rate_within_eta,
    fuel_l_per_km_exceed_days,
    rank_plants_by_cycle,
    projects_exceed_target_m3_per_load,
    wait_compare_today_vs_7day,
    quick_wins_to_utilization,
    jobs_cycle_time_over,
    driver_shortest_wait_week,
)

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
    try:
        facts = {
            "util_compare": compare_utilization(kpis, benchmark=85.0),
            "wait_by_hour": wait_by_hour(kpis["df_today"]),
            "loads_today": int(kpis["loads_today"]),
            "utilization_pct": float(kpis["utilization_pct"]),
            "prod_ratio": float(kpis["prod_ratio"]),
        }
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

# ---------------------------------
# Tool specs (JSON schema for model)
# ---------------------------------
tool_specs = [
    # Existing basics
    {
        "type": "function",
        "function": {
            "name": "compute_volume",
            "description": "Get delivered volume (m3) for a period.",
            "parameters": {"type": "object","properties": {"period": {"type": "string","enum": ["today","yesterday"]}}, "required": ["period"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_utilization",
            "description": "Compare today utilization vs a benchmark.",
            "parameters": {"type": "object","properties": {"benchmark": {"type": "number"}}, "required": []}
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
    # New tools
    {
        "type":"function","function":{
            "name":"fuel_cost_today",
            "description":"Estimate fuel cost for today’s deliveries at a given $/L.",
            "parameters":{"type":"object","properties":{"price_per_L":{"type":"number","default":1.8}}}
        }
    },
    {
        "type":"function","function":{
            "name":"co2_from_fuel_today",
            "description":"Calculate CO₂ emissions from fuel used today (kg).",
            "parameters":{"type":"object","properties":{"kg_per_L":{"type":"number","default":2.68}}}
        }
    },
    {
        "type":"function","function":{
            "name":"driver_efficiency_today",
            "description":"Rank drivers by m³/hr today (average).",
            "parameters":{"type":"object","properties":{"top_n":{"type":"integer","default":3}}}
        }
    },
    {
        "type":"function","function":{
            "name":"top_wait_jobs_48h",
            "description":"Top N jobs with the longest single-load waiting time in the last 48h.",
            "parameters":{"type":"object","properties":{"n":{"type":"integer","default":3}}}
        }
    },
    {
        "type":"function","function":{
            "name":"top_water_added_week",
            "description":"Drivers ranked by water added (L) over last 7 days.",
            "parameters":{"type":"object","properties":{"n":{"type":"integer","default":3}}}
        }
    },
    {
        "type":"function","function":{
            "name":"cycle_by_plant",
            "description":"Average cycle time by plant (today or week).",
            "parameters":{"type":"object","properties":{"period":{"type":"string","enum":["today","week"],"default":"today"}}}
        }
    },
    {
        "type":"function","function":{
            "name":"distance_over_km",
            "description":"List loads where distance_km exceeded a threshold in the last 7 days.",
            "parameters":{"type":"object","properties":{"km":{"type":"number","default":40}}}
        }
    },
    {
        "type":"function","function":{
            "name":"success_rate_within_eta",
            "description":"Delivery success rate within ±X minutes of ETA (today).",
            "parameters":{"type":"object","properties":{"tolerance_min":{"type":"number","default":10}}}
        }
    },
    {
        "type":"function","function":{
            "name":"fuel_l_per_km_exceed_days",
            "description":"Days where fleet fuel L/km exceeded a threshold over the last 7 days.",
            "parameters":{"type":"object","properties":{"threshold":{"type":"number","default":0.55}}}
        }
    },
    {
        "type":"function","function":{
            "name":"rank_plants_by_cycle",
            "description":"Rank plants by average cycle time over the last 7 days.",
            "parameters":{"type":"object","properties":{}}
        }
    },
    {
        "type":"function","function":{
            "name":"projects_exceed_target_m3_per_load",
            "description":"Projects where avg m³ per load exceeded a target (last 7 days).",
            "parameters":{"type":"object","properties":{"target":{"type":"number","default":7.6}}}
        }
    },
    {
        "type":"function","function":{
            "name":"wait_compare_today_vs_7day",
            "description":"Compare today’s avg wait vs the 7-day average.",
            "parameters":{"type":"object","properties":{}}
        }
    },
    {
        "type":"function","function":{
            "name":"quick_wins_to_utilization",
            "description":"Compute utilization gap vs target and surface hotspots to focus on.",
            "parameters":{"type":"object","properties":{"target":{"type":"number","default":88}}}
        }
    },
    {
        "type":"function","function":{
            "name":"jobs_cycle_time_over",
            "description":"Find loads where cycle time exceeded a threshold over the last 7 days.",
            "parameters":{"type":"object","properties":{"minutes":{"type":"number","default":170},"n":{"type":"integer","default":10}}}
        }
    },
    {
        "type":"function","function":{
            "name":"driver_shortest_wait_week",
            "description":"Driver(s) with shortest average waiting time in last 7 days.",
            "parameters":{"type":"object","properties":{"top_n":{"type":"integer","default":1}}}
        }
    },
]

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
    system_prompt = build_system_prompt(GUIDELINES, COACH_STYLE)
    msgs = [{"role": "system", "content": system_prompt}] + messages

    resp = client.chat.completions.create(
        model="gpt-5-chat",
        messages=msgs,
        tools=tool_specs,
        tool_choice="auto",
        temperature=0.2,
    )
    msg = resp.choices[0].message
    log_debug({"stage": "initial", "message": msg})

    if getattr(msg, "tool_calls", None):
        # handle only the first tool for simplicity
        call = msg.tool_calls[0]
        name = call.function.name
        args = json.loads(call.function.arguments or "{}")

        # Execute tool by name -------------------------
        if name == "compute_volume":
            result = compute_volume(df, period=args.get("period", "today"))
        elif name == "compare_utilization":
            result = compare_utilization(kpis, float(args.get("benchmark", 85.0)))
        elif name == "wait_by_hour":
            result = wait_by_hour(kpis["df_today"])
        elif name == "fuel_cost_today":
            result = fuel_cost_today(kpis["df_today"], float(args.get("price_per_L", 1.8)))
        elif name == "co2_from_fuel_today":
            result = co2_from_fuel_today(kpis["df_today"], float(args.get("kg_per_L", 2.68)))
        elif name == "driver_efficiency_today":
            result = driver_efficiency_today(kpis["df_today"], int(args.get("top_n", 3)))
        elif name == "top_wait_jobs_48h":
            result = top_wait_jobs_48h(kpis["df_48h"], int(args.get("n", 3)))
        elif name == "top_water_added_week":
            result = top_water_added_week(kpis["df_week"], int(args.get("n", 3)))
        elif name == "cycle_by_plant":
            result = cycle_by_plant(kpis, args.get("period", "today"))
        elif name == "distance_over_km":
            result = distance_over_km(kpis["df_week"], float(args.get("km", 40)))
        elif name == "success_rate_within_eta":
            result = success_rate_within_eta(kpis["df_today"], float(args.get("tolerance_min", 10)))
        elif name == "fuel_l_per_km_exceed_days":
            result = fuel_l_per_km_exceed_days(kpis["df_week"], float(args.get("threshold", 0.55)))
        elif name == "rank_plants_by_cycle":
            result = rank_plants_by_cycle(kpis["df_week"])
        elif name == "projects_exceed_target_m3_per_load":
            result = projects_exceed_target_m3_per_load(kpis["df_week"], float(args.get("target", 7.6)))
        elif name == "wait_compare_today_vs_7day":
            result = wait_compare_today_vs_7day(kpis["df_today"], kpis["df_week"])
        elif name == "quick_wins_to_utilization":
            result = quick_wins_to_utilization(kpis, float(args.get("target", 88)))
        elif name == "jobs_cycle_time_over":
            result = jobs_cycle_time_over(kpis["df_week"], float(args.get("minutes", 170)), int(args.get("n", 10)))
        elif name == "driver_shortest_wait_week":
            result = driver_shortest_wait_week(kpis["df_week"], int(args.get("top_n", 1)))
        else:
            result = {"ok": False, "error": f"Unknown tool: {name}"}
        # ---------------------------------------------

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

user_q = st.chat_input("Ask a question (e.g., 'Which driver added the most water this week?')")
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

# -------------
# Suggested Qs
# -------------
st.markdown("#### Suggested questions:")
cols = st.columns(2)
for i, q in enumerate(SUGGESTED_PROMPTS[:12]):
    if cols[i % 2].button(q):
        st.session_state.history.append({"role": "user", "text": q})
        st.rerun()

# -------------
# Debug panel
# -------------
if debug:
    with st.expander("🛠 Debug log"):
        st.json(st.session_state.get("debug_log", []))
