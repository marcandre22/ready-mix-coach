# coach_core.py – full KPI extraction + simple‐prompt rules

from datetime import datetime, timedelta
import pandas as pd

# Benchmarks & cost constants
BENCHMARKS = {
    "utilization_pct": 85.0,
    "fuel_per_km_threshold": 0.55,
    "rpm_discharge_min": 4,
}
COSTS = {
    "fuel_per_L": 1.80,
}

def _mins(a, b):
    if pd.isna(a) or pd.isna(b):
        return float("nan")
    return (b - a).total_seconds() / 60

def get_kpis(df: pd.DataFrame, op_minutes: int = 600) -> dict:
    """Compute all our core KPI slices and return them in a dict."""
    now = datetime.now()
    today = now.date()
    df["date"] = df["start_time"].dt.date

    # date‐based masks
    df_today     = df[df["date"] == today]
    df_yesterday = df[df["date"] == today - timedelta(days=1)]
    df_48h       = df[df["start_time"] >= now - timedelta(hours=48)]
    df_week      = df[df["start_time"] >= now - timedelta(days=7)]

    # Basic counts & volumes
    total_m3       = df["load_volume_m3"].sum()
    avg_m3         = df["load_volume_m3"].mean()
    loads_today    = len(df_today)
    loads_yesterday = len(df_yesterday)

    # Waiting & cycle
    avg_wait_today = df_today["dur_waiting"].mean() if "dur_waiting" in df_today else float("nan")
    # Use cycle_time as “productive” for now
    prod_min       = df_today["cycle_time"].sum()
    idle_min       = df_today["dur_waiting"].sum() if "dur_waiting" in df_today else 0

    # Utilization as productive ÷ (productive+idle)
    total_min      = prod_min + idle_min
    utilization_pct = (prod_min / total_min * 100) if total_min else float("nan")

    # Truck counts
    n_trucks = df_today["truck"].nunique() if "truck" in df_today else 0

    return {
        # raw slices for advanced prompts or charting
        "df": df,
        "df_today": df_today,
        "df_yesterday": df_yesterday,
        "df_48h": df_48h,
        "df_week": df_week,

        # KPIs
        "total_m3": total_m3,
        "avg_m3": avg_m3,
        "loads_today": loads_today,
        "loads_yesterday": loads_yesterday,
        "avg_wait_today": avg_wait_today,
        "prod_min": prod_min,
        "idle_min": idle_min,
        "utilization_pct": utilization_pct,
        "n_trucks": n_trucks,
    }

def handle_simple_prompt(prompt: str, kpis: dict) -> str | None:
    """
    A fast‐track router for our common SUGGESTED_PROMPTS.
    Returns a markdown‐ready string or None to fall back to GPT.
    """
    p = prompt.lower()
    df_today = kpis["df_today"]
    df_yesterday = kpis["df_yesterday"]
    df_48h = kpis["df_48h"]
    df_week = kpis["df_week"]

    # 1. Volume today vs yesterday
    if "total delivered volume today vs" in p or ("volume" in p and "today" in p and "yesterday" in p):
        return (
            f"Delivered volume today: **{kpis['total_m3']:.1f} m³**  \n"
            f"Delivered volume yesterday: **{kpis['loads_yesterday'] * df_today['load_volume_m3'].mean():.1f} m³**"
        )
    if "volume yesterday" in p:
        return f"Delivered volume yesterday: **{df_yesterday['load_volume_m3'].sum():.1f} m³**."
    if "volume today" in p:
        return f"Delivered volume today: **{df_today['load_volume_m3'].sum():.1f} m³**."

    # 2. Most water this week
    if "driver added the most water this week" in p or ("water" in p and "driver" in p and "week" in p):
        top = df_week.groupby("driver")["water_added_L"].sum().nlargest(1)
        return f"Top water‐adding driver this week is **{top.index[0]}** with **{top.values[0]:.1f} L**."

    # 3. Top three waits last 48h
    if "top three jobs with the longest wait times" in p or "longest wait" in p:
        top3 = df_48h.nlargest(3, "dur_waiting")[["job_site", "dur_waiting"]]
        lines = "\n".join(f"- {r.job_site}: {r.dur_waiting} min" for _, r in top3.iterrows())
        return f"**Top 3 longest waits (last 48 h):**\n{lines}"

    # 4. Utilization vs benchmark
    if "utilization compare" in p or ("utilization" in p and "benchmark" in p):
        actual = kpis["utilization_pct"]
        bench = BENCHMARKS["utilization_pct"]
        diff = actual - bench
        return (
            f"Today's utilization is **{actual:.1f}%**, which is **{abs(diff):.1f}% "
            f"{'above' if diff>0 else 'below'}** the {bench}% benchmark."
        )

    # 5. Fuel cost at $X/L
    if "fuel cost" in p:
        total_fuel = df_today["fuel_used_L"].sum()
        cost = COSTS["fuel_per_L"]
        return f"Estimated fuel cost for today is **${total_fuel * cost:,.2f}** (at ${cost}/L)."

    # 6. Most efficient driver by m³/hr
    if "efficient driver" in p or "m³ / hr" in p:
        df_today["prod_hr"] = df_today["load_volume_m3"] / (df_today["cycle_time"] / 60)
        top = df_today.groupby("driver")["prod_hr"].mean().nlargest(1)
        return f"Most efficient driver today is **{top.index[0]}** at **{top.values[0]:.2f} m³/hr**."

    # 7. KPI summary paragraph
    if "summarise today’s kpi performance" in p or "summarise" in p:
        return (
            f"Today’s summary:\n"
            f"- **{kpis['loads_today']} loads delivered**\n"
            f"- **{kpis['total_m3']:.1f} m³ total** (avg {kpis['avg_m3']:.1f} m³/load)\n"
            f"- **{kpis['utilization_pct']:.1f}% utilization**\n"
            f"- **{kpis['avg_wait_today']:.1f} min average wait**"
        )

    # 8. Compare wait to 7-day avg
    if "compare today’s wait time" in p or ("wait" in p and "compare" in p):
        avg7 = df_week["dur_waiting"].mean()
        today_avg = kpis["avg_wait_today"]
        diff = today_avg - avg7
        return (
            f"Avg wait today is **{today_avg:.1f} min**, which is "
            f"**{abs(diff):.1f} min {'higher' if diff>0 else 'lower'}** than the 7-day avg ({avg7:.1f} min)."
        )

    # 9. Loads today quick
    if "loads today" in p:
        return f"There were **{kpis['loads_today']}** loads delivered today."

    # ——— fallback —————————————————————————————————————————
    return None
