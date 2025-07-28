import pandas as pd

def get_kpis(df):
    kpis = {}

    # Safely compute total and average m³
    if "m3" in df.columns:
        kpis["total_m3"] = df["m3"].sum()
        kpis["avg_m3"] = df["m3"].mean()
    else:
        kpis["total_m3"] = 0
        kpis["avg_m3"] = 0

    # Number of loads (rows)
    kpis["loads_today"] = len(df) if df is not None else 0

    # Productive and idle time
    kpis["prod_min"] = df["prod_min"].sum() if "prod_min" in df.columns else 0
    kpis["idle_min"] = df["idle_min"].sum() if "idle_min" in df.columns else 0

    # Utilization % calculation
    total_min = kpis["prod_min"] + kpis["idle_min"]
    kpis["utilization_pct"] = (
        (kpis["prod_min"] / total_min) * 100 if total_min > 0 else 0
    )

    # Number of unique trucks
    kpis["n_trucks"] = df["truck"].nunique() if "truck" in df.columns else 0

    return kpis

def handle_simple_prompt(prompt, df, kpis):
    prompt = prompt.lower()

    if "volume" in prompt or "m3" in prompt:
        return f"Total delivered volume today is **{kpis['total_m3']} m³**."

    elif "loads" in prompt:
        return f"Total number of loads delivered today is **{kpis['loads_today']}**."

    elif "average size" in prompt or "avg m3" in prompt:
        return f"The average load size today is **{kpis['avg_m3']:.1f} m³**."

    elif "utilization" in prompt:
        return f"Estimated utilization today is **{kpis['utilization_pct']:.1f}%** ({kpis['prod_min']} min productive out of {kpis['n_trucks']} trucks)."

    elif "idle" in prompt:
        return f"Total idle time recorded today is **{kpis['idle_min']} minutes**."

    else:
        return "I'm not sure how to answer that yet. Try rephrasing or ask about volume, loads, size, utilization, or idle time."
