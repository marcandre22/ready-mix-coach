# coach_core.py – KPI logic with safe fields for Reporting + Chat

from datetime import datetime, timedelta
import pandas as pd

def _mins(a, b):
    if pd.isna(a) or pd.isna(b):
        return float("nan")
    return (b - a).total_seconds() / 60

def get_kpis(df: pd.DataFrame, op_minutes: int = 600) -> dict:
    """
    Compute headline KPIs for *today* and a few comparison slices.
    Returns keys used by the app safely (no missing-key crashes).
    """
    now = datetime.now()
    today = now.date()
    df = df.copy()
    df["date"] = df["start_time"].dt.date

    df_today = df[df["date"] == today]
    df_yesterday = df[df["date"] == today - timedelta(days=1)]
    df_week = df[df["start_time"] >= now - timedelta(days=7)]

    n_trucks = df_today["truck"].nunique()
    cycle_minutes = df_today["cycle_time"].sum()
    denom_minutes = op_minutes * n_trucks if n_trucks else float("nan")
    utilization_pct = (cycle_minutes / denom_minutes * 100) if denom_minutes else float("nan")

    # Productivity slices (safe if columns present)
    for col in ("ignition_on", "first_ticket", "last_return", "ignition_off"):
        if col not in df_today.columns:
            df_today[col] = pd.NaT

    df_today["min_total"] = df_today.apply(lambda r: _mins(r.ignition_on, r.ignition_off), axis=1)
    df_today["min_prod"] = df_today.apply(lambda r: _mins(r.first_ticket, r.last_return), axis=1)
    df_today["prod_ratio"] = df_today["min_prod"] / df_today["min_total"] * 100

    prod_prod_min = df_today["min_prod"].sum(skipna=True)
    prod_total_min = df_today["min_total"].sum(skipna=True)
    prod_idle_min = prod_total_min - prod_prod_min

    avg_wait_min = df_today["dur_waiting"].mean() if "dur_waiting" in df_today else float("nan")

    return {
        "df_today": df_today,
        "df_yesterday": df_yesterday,
        "df_week": df_week,
        "loads_today": int(len(df_today)),
        "loads_yesterday": int(len(df_yesterday)),
        "utilization_pct": float(utilization_pct) if pd.notna(utilization_pct) else float("nan"),
        "prod_ratio": float(df_today["prod_ratio"].mean()) if not df_today.empty else float("nan"),
        "avg_wait_min": float(avg_wait_min) if pd.notna(avg_wait_min) else float("nan"),
        "n_trucks": int(n_trucks),
        # sums used by table/chart
        "prod_prod_min": float(prod_prod_min) if pd.notna(prod_prod_min) else float("nan"),
        "prod_idle_min": float(prod_idle_min) if pd.notna(prod_idle_min) else float("nan"),
    }

def handle_simple_prompt(prompt: str, kpis: dict) -> str | None:
    """Lightweight rules so simple Qs don't hit the LLM."""
    p = (prompt or "").lower()

    if "utilization" in p:
        u = kpis.get("utilization_pct", float("nan"))
        n = kpis.get("n_trucks", 0)
        return f"Estimated utilization today is **{u:.1f}%** across **{n}** active trucks."

    if "loads today" in p or ("loads" in p and "today" in p):
        return f"There were **{kpis.get('loads_today', 0)}** loads delivered today."

    if "average wait" in p or "avg wait" in p:
        w = kpis.get("avg_wait_min", float("nan"))
        return f"Average wait time today is **{w:.1f} min**."

    return None
