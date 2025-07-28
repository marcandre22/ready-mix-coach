# coach_core.py
from datetime import datetime, timedelta
import pandas as pd

def get_kpis(df: pd.DataFrame) -> dict:
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    df_today = df[df["start_time"].dt.date == today]
    df_yest = df[df["start_time"].dt.date == yesterday]

    return {
        "today": today,
        "yesterday": yesterday,
        "df_today": df_today,
        "df_yest": df_yest,
        "wait_today": df_today["dur_waiting"].mean(),
        "wait_yest": df_yest["dur_waiting"].mean(),
        "cycle_today": df_today["cycle_time"].mean(),
        "cycle_yest": df_yest["cycle_time"].mean(),
        "vol_today": df_today["load_volume_m3"].sum(),
        "vol_yest": df_yest["load_volume_m3"].sum(),
        "loads_today": len(df_today),
        "loads_yest": len(df_yest)
    }

def handle_simple_prompt(prompt: str, kpis: dict) -> str | None:
    prompt = prompt.lower()

    if "volume" in prompt and "today" in prompt:
        return f"Today\u2019s total volume is **{kpis['vol_today']:.1f} m\u00b3** across {kpis['loads_today']} loads."

    if "wait time" in prompt and ("compare" in prompt or "yesterday" in prompt):
        delta = kpis["wait_today"] - kpis["wait_yest"]
        return (f"Average wait time today is **{kpis['wait_today']:.1f} min**, versus **{kpis['wait_yest']:.1f} min** yesterday."
                f" Difference: **{delta:+.1f} min**.")

    if "loads today" in prompt:
        return f"There were **{kpis['loads_today']}** loads delivered today."

    if "cycle time" in prompt and "today" in prompt:
        delta = kpis["cycle_today"] - kpis["cycle_yest"]
        return (f"Cycle time today is **{kpis['cycle_today']:.1f} min**, versus **{kpis['cycle_yest']:.1f} min** yesterday."
                f" Change: **{delta:+.1f} min**.")

    return None
