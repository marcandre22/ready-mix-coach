# tools.py – deterministic, grounded functions the model can call
from typing import Literal, Dict, Any, List
import pandas as pd
import numpy as np

def _ensure_date(df: pd.DataFrame) -> pd.DataFrame:
    if "date" not in df.columns:
        df = df.copy()
        df["date"] = pd.to_datetime(df["start_time"]).dt.date
    return df

# ----------------- Core basics -----------------

def compute_volume(df: pd.DataFrame, period: Literal["today", "yesterday"] = "today") -> Dict[str, Any]:
    df = _ensure_date(df)
    max_date = df["date"].max()
    target_date = max_date if period == "today" else (pd.to_datetime(max_date) - pd.Timedelta(days=1)).date()
    mask = df["date"] == target_date
    m3 = float(df.loc[mask, "load_volume_m3"].sum())
    return {"ok": True, "period": period, "date": str(target_date), "m3": m3}

def compare_utilization(kpis: dict, benchmark: float = 85.0) -> Dict[str, float]:
    actual = float(kpis.get("utilization_pct") or 0.0)
    return {"ok": True, "actual_pct": actual, "benchmark_pct": float(benchmark), "delta_pct": actual - float(benchmark)}

def wait_by_hour(df_today: pd.DataFrame) -> Dict[str, Any]:
    if df_today.empty:
        return {"ok": True, "series": []}
    g = df_today.groupby(df_today["start_time"].dt.hour)["dur_waiting"].mean().round(1)
    return {"ok": True, "series": [{"hour": int(h), "avg_wait_min": float(v)} for h, v in g.items()]}

# --------------- Cost/CO₂ ----------------------

def fuel_cost_today(df_today: pd.DataFrame, price_per_L: float = 1.8) -> Dict[str, Any]:
    total_fuel = float(df_today["fuel_used_L"].sum() if not df_today.empty else 0.0)
    return {"ok": True, "fuel_L": total_fuel, "price_per_L": price_per_L, "cost": total_fuel * price_per_L}

def co2_from_fuel_today(df_today: pd.DataFrame, kg_per_L: float = 2.68) -> Dict[str, Any]:
    total_fuel = float(df_today["fuel_used_L"].sum() if not df_today.empty else 0.0)
    return {"ok": True, "fuel_L": total_fuel, "kg_per_L": kg_per_L, "co2_kg": total_fuel * kg_per_L}

# -------------- Drivers / Jobs -----------------

def driver_efficiency_today(df_today: pd.DataFrame, top_n: int = 3) -> Dict[str, Any]:
    if df_today.empty:
        return {"ok": True, "ranking": []}
    # m3 per hour (average per driver across their loads)
    df = df_today.copy()
    df["m3_per_hr"] = df["load_volume_m3"] / (df["cycle_time"] / 60.0)
    ranking = (
        df.groupby("driver")["m3_per_hr"]
        .mean().sort_values(ascending=False).round(2)
        .head(top_n)
        .reset_index().to_dict("records")
    )
    return {"ok": True, "metric": "m3_per_hr", "ranking": ranking}

def top_wait_jobs_48h(df_48h: pd.DataFrame, n: int = 3) -> Dict[str, Any]:
    if df_48h.empty:
        return {"ok": True, "items": []}
    cols = ["ticket_id", "job_site", "driver", "dur_waiting", "start_time"]
    out = df_48h.sort_values("dur_waiting", ascending=False).head(n)[cols]
    items = out.assign(dur_waiting=lambda x: x["dur_waiting"].round(1)).to_dict("records")
    return {"ok": True, "items": items}

def top_water_added_week(df_week: pd.DataFrame, n: int = 3) -> Dict[str, Any]:
    if df_week.empty:
        return {"ok": True, "ranking": []}
    s = df_week.groupby("driver")["water_added_L"].sum().sort_values(ascending=False).head(n)
    ranking = [{"driver": idx, "water_added_L": float(val)} for idx, val in s.items()]
    return {"ok": True, "ranking": ranking}

def driver_shortest_wait_week(df_week: pd.DataFrame, top_n: int = 1) -> Dict[str, Any]:
    if df_week.empty:
        return {"ok": True, "ranking": []}
    s = df_week.groupby("driver")["dur_waiting"].mean().sort_values(ascending=True).head(top_n).round(1)
    ranking = [{"driver": idx, "avg_wait_min": float(val)} for idx, val in s.items()]
    return {"ok": True, "ranking": ranking}

# --------------- Plants / Projects -------------

def cycle_by_plant(kpis: dict, period: Literal["today","week"]="today") -> Dict[str, Any]:
    df = kpis["df_today"] if period == "today" else kpis["df_week"]
    if df.empty:
        return {"ok": True, "rows": []}
    s = df.groupby("origin_plant")["cycle_time"].mean().round(1).sort_values(ascending=True)
    rows = [{"plant": p, "avg_cycle_min": float(v)} for p, v in s.items()]
    return {"ok": True, "period": period, "rows": rows}

def rank_plants_by_cycle(df_week: pd.DataFrame) -> Dict[str, Any]:
    if df_week.empty:
        return {"ok": True, "rows": []}
    s = df_week.groupby("origin_plant")["cycle_time"].mean().round(1).sort_values()
    rows = [{"plant": p, "avg_cycle_min": float(v)} for p, v in s.items()]
    return {"ok": True, "rows": rows}

def projects_exceed_target_m3_per_load(df_week: pd.DataFrame, target: float = 7.6) -> Dict[str, Any]:
    if df_week.empty:
        return {"ok": True, "projects": []}
    s = df_week.groupby("project")["load_volume_m3"].mean()
    projects = [{"project": p, "avg_m3_per_load": float(v)} for p, v in s.items() if float(v) > target]
    return {"ok": True, "target": target, "projects": projects}

# --------------- Routing / Distance ------------

def distance_over_km(df_week: pd.DataFrame, km: float = 40.0) -> Dict[str, Any]:
    if df_week.empty:
        return {"ok": True, "items": []}
    sub = df_week[df_week["distance_km"] > km][["ticket_id","driver","origin_plant","job_site","distance_km"]]
    items = sub.sort_values("distance_km", ascending=False).head(50).to_dict("records")
    return {"ok": True, "km": km, "items": items}

# --------------- ETA success / Wait compare ----

def success_rate_within_eta(df_today: pd.DataFrame, tolerance_min: float = 10) -> Dict[str, Any]:
    if df_today.empty or "ETA" not in df_today or "actual_arrival" not in df_today:
        return {"ok": True, "rate_pct": 0.0, "counts": {"within": 0, "total": 0}}
    dif = (df_today["actual_arrival"] - df_today["ETA"]).dt.total_seconds().abs() / 60.0
    within = int((dif <= tolerance_min).sum())
    total = int(len(df_today))
    rate = (within / total * 100.0) if total else 0.0
    return {"ok": True, "rate_pct": round(rate, 1), "counts": {"within": within, "total": total}, "tolerance_min": tolerance_min}

def wait_compare_today_vs_7day(df_today: pd.DataFrame, df_week: pd.DataFrame) -> Dict[str, Any]:
    a = float(df_today["dur_waiting"].mean()) if not df_today.empty else 0.0
    b = float(df_week["dur_waiting"].mean()) if not df_week.empty else 0.0
    return {"ok": True, "avg_wait_today_min": round(a,1), "avg_wait_7day_min": round(b,1), "delta_min": round(a-b,1)}

# --------------- Fuel L/km by day --------------

def fuel_l_per_km_exceed_days(df_week: pd.DataFrame, threshold: float = 0.55) -> Dict[str, Any]:
    if df_week.empty:
        return {"ok": True, "days": []}
    df = df_week.copy()
    df["date"] = pd.to_datetime(df["start_time"]).dt.date
    g = df.groupby("date")[["fuel_used_L","distance_km"]].sum()
    g["L_per_km"] = g["fuel_used_L"] / g["distance_km"].replace(0, np.nan)
    g = g[g["L_per_km"] > threshold].round(3)
    days = [{"date": str(idx), "L_per_km": float(val)} for idx, val in g["L_per_km"].items()]
    return {"ok": True, "threshold": threshold, "days": days}

# --------------- Long cycles / anomalies -------

def jobs_cycle_time_over(df_week: pd.DataFrame, minutes: float = 170.0, n: int = 10) -> Dict[str, Any]:
    if df_week.empty:
        return {"ok": True, "items": []}
    sub = df_week[df_week["cycle_time"] > minutes][["ticket_id","driver","origin_plant","job_site","cycle_time","distance_km","dur_waiting"]]
    items = sub.sort_values("cycle_time", ascending=False).head(n).to_dict("records")
    return {"ok": True, "minutes": minutes, "items": items, "count": len(items)}

# --------------- Utilization “quick wins” ------

def quick_wins_to_utilization(kpis: dict, target: float = 88.0) -> Dict[str, Any]:
    actual = float(kpis.get("utilization_pct") or 0.0)
    gap = max(0.0, target - actual)
    # Mine hotspots from today: top waiting hour + which plant has longest avg cycle
    wb = wait_by_hour(kpis["df_today"])["series"]
    top_hour = max(wb, key=lambda x: x["avg_wait_min"]) if wb else None

    if not kpis["df_today"].empty:
        plant_cycle = kpis["df_today"].groupby("origin_plant")["cycle_time"].mean().sort_values(ascending=False)
        slowest_plant = {"plant": plant_cycle.index[0], "avg_cycle_min": float(round(plant_cycle.iloc[0],1))}
    else:
        slowest_plant = None

    suggestions = []
    if top_hour:
        suggestions.append({"action": "Stagger dispatch during peak wait hour",
                            "where": f"{top_hour['hour']}:00",
                            "why": f"avg wait {top_hour['avg_wait_min']} min"})
    if slowest_plant:
        suggestions.append({"action": "Focus cycle reduction at slowest plant",
                            "where": slowest_plant["plant"],
                            "why": f"avg cycle {slowest_plant['avg_cycle_min']} min"})

    return {"ok": True, "util_today_pct": actual, "target_pct": target, "gap_pct": round(gap,1), "hotspots": {"peak_wait_hour": top_hour, "slowest_plant": slowest_plant}, "suggestions": suggestions}
