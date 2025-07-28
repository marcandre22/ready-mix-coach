# coach_core.py – full logic coverage for all prompt types

from datetime import datetime, timedelta
import pandas as pd
import re

BENCHMARKS = {
    "utilization_pct": 85.0,
    "fuel_per_km_threshold": 0.55,
    "rpm_discharge_min": 4,
    "wait_time_cut_min": 3,
    "return_m3_alert": 0.5,
}

COSTS = {
    "fuel_per_L": 1.80,
    "overtime_per_min": 1.20,
    "m3_value": 130,
}

def _mins(a, b):
    if pd.isna(a) or pd.isna(b):
        return float("nan")
    return (b - a).total_seconds() / 60

def get_kpis(df: pd.DataFrame, op_minutes: int = 600) -> dict:
    now = datetime.now()
    today = now.date()
    df["date"] = df["start_time"].dt.date
    df["hour"] = df["start_time"].dt.hour
    df["weekday"] = df["start_time"].dt.day_name()

    df_today = df[df["date"] == today]
    df_yesterday = df[df["date"] == today - timedelta(days=1)]
    df_week = df[df["start_time"] >= now - timedelta(days=7)]
    df_48h = df[df["start_time"] >= now - timedelta(hours=48)]

    n_trucks = df_today["truck"].nunique()
    cycle_minutes = df_today["cycle_time"].sum()
    denom_minutes = op_minutes * n_trucks if n_trucks else float("nan")
    utilization_pct = (cycle_minutes / denom_minutes * 100) if denom_minutes else float("nan")

    df_today["min_total"] = df_today.apply(lambda r: _mins(r.ignition_on, r.ignition_off), axis=1)
    df_today["min_prod"] = df_today.apply(lambda r: _mins(r.first_ticket, r.last_return), axis=1)
    df_today["min_post"] = df_today.apply(lambda r: _mins(r.last_return, r.ignition_off), axis=1)
    df_today["prod_ratio"] = df_today["min_prod"] / df_today["min_total"] * 100

    return {
        "df": df,
        "df_today": df_today,
        "df_yesterday": df_yesterday,
        "df_week": df_week,
        "df_48h": df_48h,
        "loads_today": len(df_today),
        "loads_yesterday": len(df_yesterday),
        "utilization_pct": utilization_pct,
        "prod_ratio": df_today["prod_ratio"].mean(),
        "avg_wait_min": df_today["dur_waiting"].mean(),
        "n_trucks": n_trucks,
    }

def handle_simple_prompt(prompt: str, kpis: dict) -> str | None:
    p = prompt.lower()
    df = kpis["df"]
    df_today = kpis["df_today"]
    df_yesterday = kpis["df_yesterday"]
    df_week = kpis["df_week"]
    df_48h = kpis["df_48h"]

    if "volume" in p and "yesterday" in p:
        return f"Delivered volume yesterday: **{df_yesterday['load_volume_m3'].sum():.1f} m³**."

    if "volume" in p and "today" in p:
        return f"Delivered volume today: **{df_today['load_volume_m3'].sum():.1f} m³**."

    if "water" in p and "driver" in p:
        top = df_week.groupby("driver")["water_added_L"].sum().sort_values(ascending=False).head(1)
        return f"Top driver this week by water added: **{top.index[0]}** with **{top.values[0]:.1f} L**."

    if "longest wait" in p:
        top_jobs = df_48h.sort_values("dur_waiting", ascending=False).head(3)[["job_site", "dur_waiting"]]
        return "**Top 3 longest waits (last 48h):**\n" + "\n".join(
            f"- {row.job_site}: {row.dur_waiting} min" for _, row in top_jobs.iterrows())

    if "utilization" in p and "benchmark" in p:
        bench = BENCHMARKS["utilization_pct"]
        actual = kpis["utilization_pct"]
        delta = actual - bench
        status = "above" if delta > 0 else "below"
        return f"Utilization: **{actual:.1f}%**, which is **{abs(delta):.1f}% {status}** the {bench}% benchmark."

    if "fuel cost" in p:
        cost = COSTS["fuel_per_L"]
        total_fuel = df_today["fuel_used_L"].sum()
        return f"Estimated fuel cost for today: **${total_fuel * cost:,.2f}** (at ${cost}/L)."

    if "efficient driver" in p or "m³ / hr" in p:
        df_today["prod_hr"] = df_today["load_volume_m3"] / (df_today["cycle_time"] / 60)
        top = df_today.groupby("driver")["prod_hr"].mean().sort_values(ascending=False).head(1)
        return f"Most efficient driver today: **{top.index[0]}** with **{top.values[0]:.2f} m³/hr**."

    if "summarise" in p or "summary" in p:
        return (
            f"Today’s performance:
"
            f"- **{kpis['loads_today']} loads**
"
            f"- **{kpis['utilization_pct']:.1f}% utilization**
"
            f"- **{kpis['prod_ratio']:.1f}% productive time**
"
            f"- **{kpis['avg_wait_min']:.1f} min average waiting time**"
        )

    if "wait time" in p and "compare" in p:
        avg_today = df_today["dur_waiting"].mean()
        avg_week = df_week["dur_waiting"].mean()
        delta = avg_today - avg_week
        word = "more" if delta > 0 else "less"
        return f"Avg. wait today: **{avg_today:.1f} min**, which is **{abs(delta):.1f} min {word}** than 7-day avg."

    if "loads" in p and "delivered" in p and "today" in p:
        return f"Loads delivered today: **{kpis['loads_today']}**"

    return None