# coach_core.py – includes summary block + geofence + utilization
from datetime import datetime, timedelta
import pandas as pd
import re

def _mins(a, b):
    if pd.isna(a) or pd.isna(b):
        return float("nan")
    return (b - a).total_seconds() / 60

def _date_masks(df):
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    return {
        "daily": df[df["start_time"].dt.date == today],
        "wtd":   df[df["start_time"].dt.date >= monday],
        "mtd":   df[df["start_time"].dt.date >= month_start],
        "ytd":   df[df["start_time"].dt.date >= year_start],
    }

def _summary_block(df):
    if df.empty: return {}
    first = df.groupby(df["start_time"].dt.date)["start_time"].min().dt.time.mean()
    last = df.groupby(df["start_time"].dt.date)["start_time"].max().dt.time.mean()
    return {
        "m3": df["load_volume_m3"].sum(),
        "loads": len(df),
        "avg_size": df["load_volume_m3"].mean(),
        "first_avg": first.strftime("%H:%M") if pd.notna(first) else "--",
        "last_avg":  last.strftime("%H:%M") if pd.notna(last) else "--",
        "jobs": df["job_site"].nunique(),
        "trucks": df["truck"].nunique(),
        "loads_per_truck": len(df)/df["truck"].nunique() if df["truck"].nunique() else float("nan"),
        "cycle_avg": df["cycle_time"].mean(),
        "demurrage": (df["dur_waiting"] > 10).sum(),
        "excess_wash": (df["dur_washing"] > 8).sum(),
        "unscheduled": df["unscheduled_stop"].sum() if "unscheduled_stop" in df else 0,
    }

def get_kpis(df: pd.DataFrame, op_minutes: int = 600):
    today = datetime.now().date()
    df_today = df[df["start_time"].dt.date == today]

    cycle_minutes = df_today["cycle_time"].sum()
    n_trucks = df_today["truck"].nunique()
    denom = op_minutes * n_trucks if n_trucks else float("nan")
    utilization_pct = (cycle_minutes / denom * 100) if denom else float("nan")

    if {"ignition_on", "first_ticket", "last_return", "ignition_off"}.issubset(df_today.columns):
        df_today = df_today.copy()
        df_today["min_total"] = df_today.apply(lambda r: _mins(r.ignition_on, r.ignition_off), axis=1)
        df_today["min_prod"]  = df_today.apply(lambda r: _mins(r.first_ticket, r.last_return), axis=1)
        df_today["prod_ratio"] = df_today["min_prod"] / df_today["min_total"] * 100
        tot_min = df_today["min_total"].sum()
        prod_min = df_today["min_prod"].sum()
        idle_min = tot_min - prod_min
        prod_pct = prod_min / tot_min * 100 if tot_min else float("nan")
    else:
        tot_min = prod_min = idle_min = prod_pct = float("nan")

    if {"plant_in", "plant_out", "site_in", "site_out"}.issubset(df_today.columns):
        df_today["plant_dwell"] = df_today.apply(lambda r: _mins(r.plant_in, r.plant_out), axis=1)
        df_today["site_dwell"] = df_today.apply(lambda r: _mins(r.site_in, r.site_out), axis=1)

    masks = _date_masks(df)
    summary = {k: _summary_block(v) for k, v in masks.items()}

    return {
        "df_today": df_today,
        "loads_today": len(df_today),
        "cycle_today": df_today["cycle_time"].mean(),
        "utilization_pct": utilization_pct,
        "prod_total_min": tot_min,
        "prod_prod_min": prod_min,
        "prod_idle_min": idle_min,
        "prod_ratio": prod_pct,
        "n_trucks": n_trucks,
        "op_minutes": op_minutes,
        "summary": summary,
    }

def handle_simple_prompt(prompt: str, kpis: dict):
    p = prompt.lower()
    if "utilization" in p:
        return f"Utilization today is **{kpis['utilization_pct']:.1f}%** across {kpis['n_trucks']} trucks."
    if "dwell" in p or "geofence" in p:
        df = kpis["df_today"]
        plant_avg = df["plant_dwell"].mean() if "plant_dwell" in df else float("nan")
        site_avg = df["site_dwell"].mean() if "site_dwell" in df else float("nan")
        return f"Avg plant dwell time: {plant_avg:.0f} min | site dwell: {site_avg:.0f} min"
    return None
