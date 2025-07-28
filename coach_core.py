# coach_core.py – KPI logic incl. productivity (pre‑idle, productive, post‑idle)
from datetime import datetime, timedelta
import pandas as pd
import re

# -----------------------------------------------------------------------------
# 1.  KPI extraction helpers
# -----------------------------------------------------------------------------

def _mins(a, b):
    """Return minutes between two pd.Timestamp values (handles NaT)."""
    if pd.isna(a) or pd.isna(b):
        return float("nan")
    return (b - a).total_seconds() / 60


def get_kpis(df: pd.DataFrame, op_minutes: int = 600) -> dict:
    """Compute headline & productivity KPIs for *today* plus frames for further use."""

    today = datetime.now().date()
    df_today = df[df["start_time"].dt.date == today]

    # ------------------------------------------------------------------
    # Basic day‑to‑day KPIs (loads, cycle, utilization)
    # ------------------------------------------------------------------
    cycle_minutes = df_today["cycle_time"].sum()
    utilization_pct = (cycle_minutes / op_minutes * 100) if op_minutes else float("nan")

    # ------------------------------------------------------------------
    # Productivity slices (requires ignition & ticket timestamps)
    # ------------------------------------------------------------------
    if {"ignition_on", "first_ticket", "last_return", "ignition_off"}.issubset(df_today.columns):
        df_today = df_today.copy()
        df_today["min_total"] = df_today.apply(lambda r: _mins(r.ignition_on, r.ignition_off), axis=1)
        df_today["min_pre"]   = df_today.apply(lambda r: _mins(r.ignition_on, r.first_ticket), axis=1)
        df_today["min_prod"]  = df_today.apply(lambda r: _mins(r.first_ticket, r.last_return), axis=1)
        df_today["min_post"]  = df_today.apply(lambda r: _mins(r.last_return, r.ignition_off), axis=1)
        df_today["prod_ratio"] = df_today["min_prod"] / df_today["min_total"] * 100

        fleet_total_min   = df_today["min_total"].sum()
        fleet_prod_min    = df_today["min_prod"].sum()
        fleet_idle_min    = fleet_total_min - fleet_prod_min
        fleet_prod_ratio  = fleet_prod_min / fleet_total_min * 100 if fleet_total_min else float("nan")
    else:
        fleet_total_min = fleet_prod_min = fleet_idle_min = fleet_prod_ratio = float("nan")

    kpis = {
        # frames
        "df_today": df_today,
        # basic KPIs
        "loads_today": len(df_today),
        "cycle_today": df_today["cycle_time"].mean(),
        "utilization_pct": utilization_pct,
        "op_minutes": op_minutes,
        # productivity fleet aggregates
        "prod_total_min": fleet_total_min,
        "prod_prod_min":  fleet_prod_min,
        "prod_idle_min":  fleet_idle_min,
        "prod_ratio":     fleet_prod_ratio,
    }

    return kpis

# -----------------------------------------------------------------------------
# 2.  Rule‑based prompt handler (fast answers without GPT)
# -----------------------------------------------------------------------------

def handle_simple_prompt(prompt: str, kpis: dict) -> str | None:
    p = prompt.lower()

    # ---------------- Utilization (10‑h default or custom hours) ------------
    if "utilization" in p:
        custom_hours = re.search(r'(\d+(\.\d+)?)\s*(hour|hr|h)', p)
        if custom_hours:
            op_min = float(custom_hours.group(1)) * 60
            cycle_min = kpis["df_today"]["cycle_time"].sum()
            util = (cycle_min / op_min * 100) if op_min else float("nan")
            return f"Estimated utilization for today is **{util:.1f}%**, based on a {custom_hours.group(1)}‑hour window."
        return f"Estimated utilization for today is **{kpis['utilization_pct']:.1f}%** (10‑hour default window)."

    # ---------------- Productivity ratio (productive vs idle) --------------
    if any(kw in p for kw in ["productive", "idle", "productivity ratio", "truck productivity"]):
        ratio = kpis["prod_ratio"]
        prod_h = kpis["prod_prod_min"] / 60
        idle_h = kpis["prod_idle_min"] / 60
        return (f"Fleet‑wide today: **{ratio:.1f}% productive** (≈ {prod_h:,.1f} hr) vs **{idle_h:,.1f} hr idle**."
                " Try asking: ‘Which truck had the most idle time?’ for details.")

    # ---------------- Additional quick replies (loads today, etc.) ----------
    if "loads today" in p:
        return f"There were **{kpis['loads_today']}** loads delivered today."

    return None  # fall back to GPT if not matched
