from datetime import datetime, timedelta
import pandas as pd
import re

# -----------------------------------------------------------------------------
# 1.  Helper
# -----------------------------------------------------------------------------

def _mins(a, b):
    if pd.isna(a) or pd.isna(b):
        return float("nan")
    return (b - a).total_seconds() / 60

# -----------------------------------------------------------------------------
# 2.  KPI extraction
# -----------------------------------------------------------------------------

def get_kpis(df: pd.DataFrame, op_minutes: int = 600) -> dict:
    """Return today’s KPIs; `op_minutes` is the shift length per truck (default 10 h)."""

    today = datetime.now().date()
    df_today = df[df["start_time"].dt.date == today]

    # ---------- Basic day KPIs ------------------------------------------------
    cycle_minutes = df_today["cycle_time"].sum()
    n_trucks = df_today["truck"].nunique()
    denom_minutes = op_minutes * n_trucks if n_trucks else float("nan")
    utilization_pct = (cycle_minutes / denom_minutes * 100) if denom_minutes else float("nan")

    # ---------- Productivity slices ------------------------------------------
    if {"ignition_on", "first_ticket", "last_return", "ignition_off"}.issubset(df_today.columns):
        df_today = df_today.copy()
        df_today["min_total"] = df_today.apply(lambda r: _mins(r.ignition_on, r.ignition_off), axis=1)
        df_today["min_pre"]   = df_today.apply(lambda r: _mins(r.ignition_on, r.first_ticket), axis=1)
        df_today["min_prod"]  = df_today.apply(lambda r: _mins(r.first_ticket, r.last_return), axis=1)
        df_today["min_post"]  = df_today.apply(lambda r: _mins(r.last_return, r.ignition_off), axis=1)
        df_today["prod_ratio"] = df_today["min_prod"] / df_today["min_total"] * 100

        tot_min  = df_today["min_total"].sum()
        prod_min = df_today["min_prod"].sum()
        idle_min = tot_min - prod_min
        prod_pct = prod_min / tot_min * 100 if tot_min else float("nan")
    else:
        tot_min = prod_min = idle_min = prod_pct = float("nan")

    # ---------- Summary
    summary = {
        "loads": len(df_today),
        "m3": df_today["load_volume_m3"].sum() if "load_volume_m3" in df_today else float("nan"),
        "avg_m3": df_today["load_volume_m3"].mean() if "load_volume_m3" in df_today else float("nan"),
        "utilization": utilization_pct,
        "prod_ratio": prod_pct,
        "idle_min": idle_min,
        "prod_min": prod_min,
        "n_trucks": n_trucks,
    }

    return {
        "df_today": df_today,
        "summary": {"daily": summary},
        "loads_today": summary["loads"],
        "cycle_today": df_today["cycle_time"].mean(),
        "utilization_pct": utilization_pct,
        "prod_total_min": tot_min,
        "prod_prod_min": prod_min,
        "prod_idle_min": idle_min,
        "prod_ratio": prod_pct,
        "op_minutes": op_minutes,
        "n_trucks": n_trucks,
    }

# -----------------------------------------------------------------------------
# 3.  Quick‑answer rules
# -----------------------------------------------------------------------------

def handle_simple_prompt(prompt: str, kpis: dict) -> str | None:
    p = prompt.lower()
    summary = kpis.get("summary", {}).get("daily", {})

    if "utilization" in p:
        custom_hours = re.search(r'(\d+(\.\d+)?)\s*(hour|hr|h)', p)
        n_trucks = kpis["n_trucks"] or 1
        if custom_hours:
            op_min = float(custom_hours.group(1)) * 60 * n_trucks
            util = (kpis["df_today"]["cycle_time"].sum() / op_min * 100) if op_min else float("nan")
            return f"Estimated utilization today is **{util:.1f}%** (window: {custom_hours.group(1)} h × {n_trucks} trucks)."
        return f"Estimated utilization today is **{kpis['utilization_pct']:.1f}%** (10 h × {n_trucks} trucks)."

    if any(kw in p for kw in ["productive", "idle", "productivity ratio", "truck productivity"]):
        r = kpis["prod_ratio"]
        prod_h = kpis["prod_prod_min"] / 60
        idle_h = kpis["prod_idle_min"] / 60
        return f"Fleet today: **{r:.1f}% productive** (≈ {prod_h:.1f} h) vs **{idle_h:.1f} h idle)."

    if "loads today" in p or "how many loads" in p:
        return f"There were **{summary.get('loads', 0)}** loads delivered today."

    if "average volume" in p or "avg. volume" in p or "volume today" in p:
        return f"Today’s total delivered volume is **{summary.get('m3', 0):.1f} m³**, average per load is **{summary.get('avg_m3', 0):.1f} m³**."

    if "loads per truck" in p:
        val = summary.get("loads", 0) / summary.get("n_trucks", 1)
        return f"Loads per truck today: **{val:.2f}**"

    if "waiting" in p or "idle" in p:
        idle = summary.get("idle_min", 0) / 60
        return f"Total waiting time across the fleet today is approximately **{idle:.1f} hours**."

    if "fuel" in p:
        return "Fuel usage analysis is not enabled in this version."

    if "geofence" in p or "dwell" in p:
        return "Time spent at plants and job sites (geofenced zones) is currently not implemented."

    # Log unknown prompt
    st = __import__('streamlit')
    st.session_state.setdefault("unhandled_prompts", [])
    st.session_state["unhandled_prompts"].append(prompt)

    return None