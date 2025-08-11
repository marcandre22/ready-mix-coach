# coach_core.py – KPI logic with safe fields + quick-answer rules

from datetime import datetime, timedelta
import os
import pandas as pd
import re

def _mins(a, b):
    if pd.isna(a) or pd.isna(b):
        return float("nan")
    return (b - a).total_seconds() / 60

def get_kpis(df: pd.DataFrame, op_minutes: int = 600) -> dict:
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

    # Safe columns
    for col in ("ignition_on", "first_ticket", "last_return", "ignition_off"):
        if col not in df_today.columns:
            df_today[col] = pd.NaT

    df_today["min_total"] = df_today.apply(lambda r: _mins(r.ignition_on, r.ignition_off), axis=1)
    df_today["min_prod"]  = df_today.apply(lambda r: _mins(r.first_ticket, r.last_return), axis=1)
    df_today["prod_ratio"] = df_today["min_prod"] / df_today["min_total"] * 100

    prod_prod_min = df_today["min_prod"].sum(skipna=True)
    prod_total_min = df_today["min_total"].sum(skipna=True)
    prod_idle_min = prod_total_min - prod_prod_min

    # Totals we’ll reuse for quick answers
    fuel_L_today = df_today["fuel_used_L"].sum() if "fuel_used_L" in df_today else float("nan")
    distance_km_today = df_today["distance_km"].sum() if "distance_km" in df_today else float("nan")
    m3_today = df_today["load_volume_m3"].sum() if "load_volume_m3" in df_today else float("nan")

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
        "prod_prod_min": float(prod_prod_min) if pd.notna(prod_prod_min) else float("nan"),
        "prod_idle_min": float(prod_idle_min) if pd.notna(prod_idle_min) else float("nan"),
        "fuel_L_today": float(fuel_L_today) if pd.notna(fuel_L_today) else float("nan"),
        "distance_km_today": float(distance_km_today) if pd.notna(distance_km_today) else float("nan"),
        "m3_today": float(m3_today) if pd.notna(m3_today) else float("nan"),
    }


def _extract_price_per_L(text: str) -> float | None:
    """Find a price like 1.80, $1.80, 1,80 etc."""
    # matches 1.8 or 1,80 optionally prefixed by $ and optionally followed by /L
    m = re.search(r"\$?\s*(\d+(?:[.,]\d+)?)\s*(?:/|per)?\s*[lL]", text)
    if not m:
        m = re.search(r"\$?\s*(\d+(?:[.,]\d+)?)", text)  # last resort
    if not m:
        return None
    return float(m.group(1).replace(",", "."))


def handle_simple_prompt(prompt: str, kpis: dict) -> str | None:
    """Lightweight rules so simple Qs don't hit the LLM."""
    p = (prompt or "").lower()

    # Utilization
    if "utilization" in p:
        u = kpis.get("utilization_pct", float("nan"))
        n = kpis.get("n_trucks", 0)
        return f"Estimated utilization today is **{u:.1f}%** across **{n}** active trucks."

    # Loads
    if "loads today" in p or ("loads" in p and "today" in p):
        return f"There were **{kpis.get('loads_today', 0)}** loads delivered today."

    # Avg wait
    if "average wait" in p or "avg wait" in p:
        w = kpis.get("avg_wait_min", float("nan"))
        return f"Average wait time today is **{w:.1f} min**."

    # Fuel cost today at $X/L
    if "fuel" in p and "cost" in p and ("/l" in p or "per l" in p or "$" in p):
        price = _extract_price_per_L(p)
        if price is None:
            return "Please include the price per litre (e.g., **$1.80/L**) and try again."
        L = kpis.get("fuel_L_today", float("nan"))
        if pd.isna(L):
            return "I don't have fuel data for today."
        return f"Fuel used today ≈ **{L:,.1f} L** → cost at **${price:.2f}/L** ≈ **${L*price:,.2f}**."

    # CO2 emissions today from fuel
    if ("co2" in p or "emission" in p) and ("today" in p or "for today" in p or "my fuel" in p):
        L = kpis.get("fuel_L_today", float("nan"))
        if pd.isna(L) or L <= 0:
            return "I don't have fuel usage for today, so I can't compute CO₂."

        # basic factors (kg CO2 per litre)
        FACTORS = {"diesel": 2.68, "gasoline": 2.31}
        default_type = os.getenv("COACH_DEFAULT_FUEL", "diesel").lower()
        fuel_type = "gasoline" if any(x in p for x in ["gasoline", "petrol", "gaso"]) else \
                    "diesel" if "diesel" in p else default_type

        factor = FACTORS.get(fuel_type, FACTORS["diesel"])
        kg = L * factor
        t = kg / 1000.0
        return (
            f"CO₂ estimate for **today** using **{fuel_type}**:\n"
            f"- Fuel used: **{L:,.1f} L**\n"
            f"- Emission factor: **{factor:.2f} kg CO₂/L**\n"
            f"- CO₂ emitted: **{kg:,.0f} kg** (≈ **{t:.3f} t**)"
        )

    return None
