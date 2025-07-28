# coach_core.py – expanded KPI logic (fuel, distance, 7‑ & 30‑day averages)
from datetime import datetime, timedelta
import pandas as pd

# ----------------------------------------------------------------------------
# 1.  KPI extraction helpers
# ----------------------------------------------------------------------------

def get_kpis(df: pd.DataFrame) -> dict:
    """Return a dictionary of all headline KPIs we may want to answer quickly."""

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    last_7_days  = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)

    # Slice data
    df_today  = df[df["start_time"].dt.date == today]
    df_yest   = df[df["start_time"].dt.date == yesterday]
    df_7day   = df[df["start_time"].dt.date >= last_7_days]
    df_30day  = df[df["start_time"].dt.date >= last_30_days]

    # Group by date for daily aggregates (used for rolling averages)
    grouped_7d   = df_7day.groupby(df_7day["start_time"].dt.date)
    grouped_30d  = df_30day.groupby(df_30day["start_time"].dt.date)

    # Helper lambdas
    _sum   = lambda d, col: float("nan") if d.empty else d[col].sum()
    _mean  = lambda d, col: float("nan") if d.empty else d[col].mean()

    return {
        # raw frames
        "df_today": df_today,
        "df_yest": df_yest,
        "df_7day": df_7day,
        "df_30day": df_30day,
        # headline day‑to‑day KPIs
        "vol_today":  _sum(df_today,  "load_volume_m3"),
        "vol_yest":   _sum(df_yest,   "load_volume_m3"),
        "wait_today": _mean(df_today, "dur_waiting"),
        "wait_yest":  _mean(df_yest,  "dur_waiting"),
        "cycle_today": _mean(df_today, "cycle_time"),
        "cycle_yest":  _mean(df_yest,  "cycle_time"),
        "loads_today": len(df_today),
        "loads_yest":  len(df_yest),
        "fuel_today":  _sum(df_today,  "fuel_used_L"),
        "fuel_yest":   _sum(df_yest,   "fuel_used_L"),
        "dist_today":  _sum(df_today,  "distance_km"),
        "dist_yest":   _sum(df_yest,   "distance_km"),
        # 7‑day averages (daily)
        "avg_vol_7d":   grouped_7d["load_volume_m3"].sum().mean(),
        "avg_wait_7d":  grouped_7d["dur_waiting"].mean().mean(),
        "avg_cycle_7d": grouped_7d["cycle_time"].mean().mean(),
        "avg_loads_7d": grouped_7d.size().mean(),
        "avg_fuel_7d":  grouped_7d["fuel_used_L"].sum().mean(),
        "avg_dist_7d":  grouped_7d["distance_km"].sum().mean(),
        # 30‑day averages (daily)
        "avg_vol_30d":   grouped_30d["load_volume_m3"].sum().mean(),
        "avg_wait_30d":  grouped_30d["dur_waiting"].mean().mean(),
        "avg_cycle_30d": grouped_30d["cycle_time"].mean().mean(),
        "avg_loads_30d": grouped_30d.size().mean(),
        "avg_fuel_30d":  grouped_30d["fuel_used_L"].sum().mean(),
        "avg_dist_30d":  grouped_30d["distance_km"].sum().mean(),
        "days_7d":  grouped_7d.ngroups,
        "days_30d": grouped_30d.ngroups,
    }

# ----------------------------------------------------------------------------
# 2.  Rule‑based prompt handler (fast answers, no GPT call)
# ----------------------------------------------------------------------------

def handle_simple_prompt(prompt: str, kpis: dict) -> str | None:
    """Return an answer string if we can satisfy the prompt locally, else None."""

    p = prompt.lower()

    # ---------------------------------------------------------------------
    # Quick compare today vs yesterday
    # ---------------------------------------------------------------------
    compare_map = {
        "volume":  ("vol_today",  "vol_yest",  "m³"),
        "wait":    ("wait_today", "wait_yest", "min"),
        "wait time": ("wait_today", "wait_yest", "min"),
        "cycle":   ("cycle_today","cycle_yest","min"),
        "cycle time": ("cycle_today","cycle_yest","min"),
        "fuel":    ("fuel_today", "fuel_yest", "L"),
        "distance":("dist_today", "dist_yest", "km"),
        "loads":   ("loads_today","loads_yest", ""),
    }
    if ("compare" in p or "yesterday" in p):
        for kw, (today_key, yest_key, unit) in compare_map.items():
            if kw in p:
                today_val, yest_val = kpis[today_key], kpis[yest_key]
                delta = today_val - yest_val
                unit_str = f" {unit}" if unit else ""
                return (f"Today’s {kw} is **{today_val:,.1f}{unit_str}**, vs **{yest_val:,.1f}{unit_str}** yesterday."
                        f" Difference: **{delta:+.1f}{unit_str}**.")

    # ---------------------------------------------------------------------
    # Today‑only singles (e.g. "fuel today" / "volume today")
    # ---------------------------------------------------------------------
    singles_map = {
        "volume":  ("vol_today", "m³"),
        "wait":    ("wait_today", "min"),
        "wait time": ("wait_today", "min"),
        "cycle":   ("cycle_today", "min"),
        "cycle time": ("cycle_today", "min"),
        "fuel":    ("fuel_today", "L"),
        "distance":("dist_today", "km"),
        "loads":   ("loads_today", ""),
    }
    if "today" in p:
        for kw, (key, unit) in singles_map.items():
            if kw in p:
                val = kpis[key]
                unit_str = f" {unit}" if unit else ""
                if kw == "loads":
                    return f"There were **{int(val)}** loads delivered today."
                return f"Today’s {kw} is **{val:,.1f}{unit_str}**."

    # ---------------------------------------------------------------------
    # Rolling averages – 7‑day / 30‑day
    # ---------------------------------------------------------------------
    avg_map = {
        "volume":  ("avg_vol",  "m³"),
        "wait":    ("avg_wait", "min"),
        "wait time": ("avg_wait", "min"),
        "cycle":   ("avg_cycle","min"),
        "cycle time": ("avg_cycle","min"),
        "fuel":    ("avg_fuel", "L"),
        "distance":("avg_dist", "km"),
        "loads":   ("avg_loads", ""),
    }
    for period_kw, period_suffix in [("7", "7d"), ("30", "30d")]:
        if (period_kw in p and "average" in p):
            for kw, (base_key, unit) in avg_map.items():
                if kw in p:
                    key = f"{base_key}_{period_suffix}"
                    val = kpis[key]
                    unit_str = f" {unit}" if unit else ""
                    return f"Average {kw} over the last {period_kw} days is **{val:,.1f}{unit_str}**."

    return None  # Fall back to GPT if nothing matched
