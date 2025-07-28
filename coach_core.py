# coach_core.py – updated with summary key for app compatibility

from datetime import datetime, timedelta
import pandas as pd
import re

def _mins(a, b):
    if pd.isna(a) or pd.isna(b):
        return float("nan")
    return (b - a).total_seconds() / 60

def get_kpis(df: pd.DataFrame, op_minutes: int = 600) -> dict:
    now = datetime.now()
    today = now.date()
    df["date"] = df["start_time"].dt.date
    df_today = df[df["date"] == today]

    n_trucks = df_today["truck"].nunique()
    cycle_minutes = df_today["cycle_time"].sum()
    denom_minutes = op_minutes * n_trucks if n_trucks else float("nan")
    utilization_pct = (cycle_minutes / denom_minutes * 100) if denom_minutes else float("nan")

    df_today["min_total"] = df_today.apply(lambda r: _mins(r.ignition_on, r.ignition_off), axis=1)
    df_today["min_prod"] = df_today.apply(lambda r: _mins(r.first_ticket, r.last_return), axis=1)
    df_today["min_post"] = df_today.apply(lambda r: _mins(r.last_return, r.ignition_off), axis=1)
    df_today["prod_ratio"] = df_today["min_prod"] / df_today["min_total"] * 100

    summary = {
        "loads": len(df_today),
        "volume_m3": df_today["load_volume_m3"].sum(),
        "avg_cycle": df_today["cycle_time"].mean(),
        "utilization": utilization_pct,
        "productive_ratio": df_today["prod_ratio"].mean(),
        "idle_min": df_today["min_post"].sum(),
        "prod_min": df_today["min_prod"].sum(),
        "n_trucks": n_trucks
    }

    return {
        "df": df,
        "df_today": df_today,
        "loads_today": len(df_today),
        "cycle_today": df_today["cycle_time"].mean(),
        "utilization_pct": utilization_pct,
        "prod_ratio": df_today["prod_ratio"].mean(),
        "prod_idle_min": df_today["min_post"].sum(),
        "prod_prod_min": df_today["min_prod"].sum(),
        "n_trucks": n_trucks,
        "summary": summary
    }

def handle_simple_prompt(prompt: str, kpis: dict) -> str | None:
    p = prompt.lower()

    if "loads" in p and "today" in p:
        return f"There were **{kpis['loads_today']}** loads delivered today."

    if "utilization" in p:
        return f"Estimated utilization today is **{kpis['utilization_pct']:.1f}%**."

    if "productive" in p or "productivity ratio" in p:
        return f"Productive ratio today: **{kpis['prod_ratio']:.1f}%**."

    return None