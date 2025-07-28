# coach_core.py – KPI logic incl. productivity & corrected utilization
from datetime import datetime, timedelta
import pandas as pd
import re

# ---------------------------------------------------------------------
# 1. Helpers
# ---------------------------------------------------------------------
def _mins(a, b):
    """Return minutes between two pd.Timestamp values (handles NaT)."""
    if pd.isna(a) or pd.isna(b):
        return float("nan")
    return (b - a).total_seconds() / 60


# ---------------------------------------------------------------------
# 2. KPI extraction
# ---------------------------------------------------------------------
def get_kpis(df: pd.DataFrame, op_minutes: int = 600) -> dict:
    """
    Compute headline KPIs for *today*.
    `op_minutes` is the nominal shift length PER TRUCK (default 10 h = 600 min).
    """
    today = datetime.now().date()
    df_today = df[df["start_time"].dt.date == today]

    # ----- Utilization ------------------------------------------------
    cycle_minutes = df_today["cycle_time"].sum()
    n_trucks = df_today["truck"].nunique()
    denom = op_minutes * n_trucks if n_trucks else float("nan")
    utilization_pct = (cycle_minutes / denom * 100) if denom else float("nan")

    # ----- Productivity slices ---------------------------------------
    if {"ignition_on", "first_ticket", "last_return", "ignition_off"}.issubset(df_today.columns):
        df_today = df_today.copy()
        df_today["min_total"] = df_today.apply(lambda r: _mins(r.ignition_on, r.ignition_off), axis=1)
        df_today["min_prod"]  = df_today.apply(lambda r: _mins(r.first_ticket, r.last_return), axis=1)
        df_today["prod_ratio"] = df_today["min_prod"] / df_today["min_total"] * 100

        tot_min  = df_today["min_total"].sum()
        prod_min = df_today["min_prod"].sum()
        idle_min = tot_min - prod_min
        prod_pct = prod_min / tot_min * 100 if tot_min else float("nan")
    else:
        tot_min = prod_min = idle_min = prod_pct = float("nan")

    return {
        "df_today": df_today,
        "loads_today": len(df_today),
        "cycle_today": df_today["cycle_time"].mean(),
        "utilization_pct": utilization_pct,
        "prod_total_min": tot_min,
        "prod_prod_min": prod_min,
        "prod_idle_min": idle_min,
        "prod_ratio": prod_pct,
        "op_minutes": op_minutes,
        "n_trucks": n_trucks,
    }


# ---------------------------------------------------------------------
# 3. Quick-answer rules (skip GPT when possible)
# ---------------------------------------------------------------------
def handle_simple_prompt(prompt: str, kpis: dict) -> str | None:
    p = prompt.lower()

    # Utilization ------------------------------------------------------
    if "utilization" in p:
        custom = re.search(r"(\\d+(?:\\.\\d+)?)\\s*(hour|hr|h)", p)
        n = kpis["n_trucks"] or 1
        if custom:
            op_min = float(custom.group(1)) * 60 * n
            util = (kpis["df_today"]["cycle_time"].sum() / op_min * 100) if op_min else float("nan")
            return f"Estimated utilization today is **{util:.1f}%** (window: {custom.group(1)} h × {n} trucks)."
        return f"Estimated utilization today is **{kpis['utilization_pct']:.1f}%** (10 h × {n} trucks)."

    # Productivity ratio ----------------------------------------------
    if any(kw in p for kw in ["productive", "idle", "productivity ratio", "truck productivity"]):
        r = kpis["prod_ratio"]
        prod_h = kpis["prod_prod_min"] / 60
        idle_h = kpis["prod_idle_min"] / 60
        return (
            f"Fleet today: **{r:.1f}% productive** "
            f"(≈ {prod_h:.1f} h productive vs {idle_h:.1f} h idle)."
        )

    # Quick loads today
    if "loads today" in p:
        return f"There were **{kpis['loads_today']}** loads delivered today."

    return None
