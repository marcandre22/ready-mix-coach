# coach_core.py – KPI logic incl. productivity & “m³” fix

from datetime import datetime, timedelta
import pandas as pd
import re

def _mins(a, b):
    if pd.isna(a) or pd.isna(b):
        return float("nan")
    return (b - a).total_seconds() / 60

def get_kpis(df: pd.DataFrame, op_minutes: int = 600) -> dict:
    """
    Compute headline KPIs for *today*.
    Expects `load_volume_m3` in df.
    """
    now = datetime.now()
    today = now.date()

    # make sure we have a date column
    df["date"] = df["start_time"].dt.date

    df_today = df[df["date"] == today]
    df_yesterday = df[df["date"] == today - timedelta(days=1)]
    df_week = df[df["start_time"] >= now - timedelta(days=7)]
    df_48h = df[df["start_time"] >= now - timedelta(hours=48)]

    # Utilization
    n_trucks = df_today["truck"].nunique()
    cycle_minutes = df_today["cycle_time"].sum()
    denom = op_minutes * n_trucks if n_trucks else float("nan")
    utilization_pct = (cycle_minutes / denom * 100) if denom else float("nan")

    # Productivity slices
    if {"ignition_on", "first_ticket", "last_return", "ignition_off"}.issubset(df_today.columns):
        df_today = df_today.copy()
        df_today["min_total"] = df_today.apply(lambda r: _mins(r.ignition_on, r.ignition_off), axis=1)
        df_today["min_prod"]  = df_today.apply(lambda r: _mins(r.first_ticket, r.last_return), axis=1)
        df_today["prod_ratio"] = df_today["min_prod"] / df_today["min_total"] * 100
        tot_min  = df_today["min_total"].sum()
        prod_min = df_today["min_prod"].sum()
        idle_min = tot_min - prod_min
    else:
        tot_min = prod_min = idle_min = float("nan")

    return {
        # raw slices
        "df_today":     df_today,
        "df_yesterday": df_yesterday,
        "df_week":      df_week,
        "df_48h":       df_48h,

        # counts & sums
        "loads_today":     len(df_today),
        "loads_yesterday": len(df_yesterday),

        # utilization & productivity
        "utilization_pct": utilization_pct,
        "prod_ratio":      df_today["prod_ratio"].mean() if "prod_ratio" in df_today else float("nan"),
        "prod_total_min":  tot_min,
        "prod_prod_min":   prod_min,
        "prod_idle_min":   idle_min,

        # waiting
        "avg_wait_min":    df_today["dur_waiting"].mean() if "dur_waiting" in df_today else float("nan"),

        # m³ delivery
        "total_m3":        df_today["load_volume_m3"].sum(),
        "avg_m3":          df_today["load_volume_m3"].mean(),

        # meta
        "n_trucks":        n_trucks,
        "op_minutes":      op_minutes,
    }

def handle_simple_prompt(prompt: str, kpis: dict) -> str | None:
    """
    Quick rules to short-circuit certain queries.
    """
    p = prompt.lower()

    if "volume" in p and "yesterday" in p:
        return f"Delivered volume yesterday: **{kpis['total_m3']:.1f} m³**."
    if "volume" in p and "today" in p:
        return f"Delivered volume today: **{kpis['total_m3']:.1f} m³**."
    if "loads" in p and "today" in p:
        return f"Loads delivered today: **{kpis['loads_today']}**."
    if "utilization" in p:
        return f"Utilization today: **{kpis['utilization_pct']:.1f}%** across {kpis['n_trucks']} trucks."
    # …add more here as needed…
    return None
