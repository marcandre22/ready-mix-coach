# coach_core.py

def get_kpis(df):
    kpis = {
        "loads_today": len(df),
        "total_m3": df["m3"].sum(),
        "avg_m3": df["m3"].mean() if not df.empty else 0,
        "prod_idle_min": df["idle_min"].sum(),
        "prod_prod_min": df["prod_min"].sum(),
        "utilization_pct": round(df["prod_min"].sum() / (df["n_trucks"].iloc[0] * 60 * 10) * 100, 2)
            if not df.empty and df["n_trucks"].iloc[0] else 0,
        "n_trucks": df["n_trucks"].iloc[0] if not df.empty else 0,
        "summary": {
            "daily": {
                "loads": len(df),
                "m3": df["m3"].sum(),
                "avg_size": df["m3"].mean() if not df.empty else 0,
                "utilization": round(df["prod_min"].sum() / (df["n_trucks"].iloc[0] * 60 * 10) * 100, 2)
                    if not df.empty and df["n_trucks"].iloc[0] else 0,
                "prod_ratio": round(df["prod_min"].sum() / df["idle_min"].sum(), 2)
                    if df["idle_min"].sum() > 0 else 0,
                "idle_min": df["idle_min"].sum(),
                "prod_min": df["prod_min"].sum(),
                "n_trucks": df["n_trucks"].iloc[0] if not df.empty else 0,
            }
        },
        "df_today": df
    }
    return kpis


def handle_simple_prompt(prompt, kpis):
    p = prompt.lower()

    if "volume" in p and "yesterday" in p:
        return "We don't have yesterday's data loaded right now — only today's volume is available."

    elif "volume" in p and "today" in p:
        return f"Today's delivered volume is **{kpis['total_m3']:.1f} m³** across {kpis['loads_today']} loads."

    elif "utilization" in p:
        return f"Estimated utilization today is **{kpis['utilization_pct']:.1f}%**."

    elif "summary" in p:
        return (
            f"Today we ran {kpis['loads_today']} loads totaling {kpis['total_m3']} m³. "
            f"Average load size was {kpis['avg_m3']:.1f} m³. Utilization was {kpis['utilization_pct']:.1f}%."
        )

    return None