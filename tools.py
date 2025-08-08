# tools.py – deterministic, grounded functions the model can call
from typing import Literal, Dict, Any
import pandas as pd

def compute_volume(df: pd.DataFrame, period: Literal["today", "yesterday"] = "today") -> Dict[str, Any]:
    if "date" not in df.columns:
        df = df.copy()
        df["date"] = pd.to_datetime(df["start_time"]).dt.date

    max_date = df["date"].max()
    target_date = max_date if period == "today" else (pd.to_datetime(max_date) - pd.Timedelta(days=1)).date()
    mask = df["date"] == target_date
    m3 = float(df.loc[mask, "load_volume_m3"].sum())
    return {"period": period, "date": str(target_date), "m3": m3}

def compare_utilization(kpis: dict, benchmark: float = 85.0) -> Dict[str, float]:
    actual = float(kpis.get("utilization_pct") or 0.0)
    return {"actual_pct": actual, "benchmark_pct": float(benchmark), "delta_pct": actual - float(benchmark)}

def wait_by_hour(df_today: pd.DataFrame) -> Dict[str, Any]:
    if df_today.empty:
        return {"series": []}
    g = df_today.groupby(df_today["start_time"].dt.hour)["dur_waiting"].mean().round(1)
    return {"series": [{"hour": int(h), "avg_wait_min": float(v)} for h, v in g.items()]}
