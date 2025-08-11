# coach_core.py – KPI logic + full coverage for suggestion prompts

from datetime import datetime, timedelta
import os
import math
import re
import pandas as pd


# -------------------------
# Helpers
# -------------------------
def _mins(a, b):
    if pd.isna(a) or pd.isna(b):
        return float("nan")
    return (b - a).total_seconds() / 60


def _safe_mean(series: pd.Series) -> float:
    if series is None or len(series) == 0:
        return float("nan")
    m = series.mean()
    return float(m) if pd.notna(m) else float("nan")


def _price_from_text(text: str) -> float | None:
    m = re.search(r"\$?\s*(\d+(?:[.,]\d+)?)\s*(?:/|per)?\s*[lL]", text)
    if not m:
        m = re.search(r"\$?\s*(\d+(?:[.,]\d+)?)", text)
    if not m:
        return None
    return float(m.group(1).replace(",", "."))


# -------------------------
# KPI Extraction
# -------------------------
def get_kpis(df: pd.DataFrame, op_minutes: int = 600) -> dict:
    """
    Compute KPIs and return a dict with slices:
    - df_today / df_yesterday / df_week / df_48h
    - headline KPIs (loads, utilization, wait, etc.)
    - totals for fuel, distance, m3
    """
    now = datetime.now()
    today = now.date()
    df = df.copy()
    df["date"] = df["start_time"].dt.date
    df["hour"] = df["start_time"].dt.hour

    df_today = df[df["date"] == today]
    df_yesterday = df[df["date"] == today - timedelta(days=1)]
    df_week = df[df["start_time"] >= now - timedelta(days=7)]
    df_48h = df[df["start_time"] >= now - timedelta(hours=48)]

    # Utilization today
    n_trucks_today = df_today["truck"].nunique()
    cycle_minutes_today = df_today["cycle_time"].sum()
    denom_today = op_minutes * n_trucks_today if n_trucks_today else float("nan")
    utilization_today = (cycle_minutes_today / denom_today * 100) if denom_today else float("nan")

    # Productivity today (plant/site dwell safety)
    for c in ("ignition_on", "first_ticket", "last_return", "ignition_off"):
        if c not in df_today.columns:
            df_today[c] = pd.NaT
    df_today["min_total"] = df_today.apply(lambda r: _mins(r.ignition_on, r.ignition_off), axis=1)
    df_today["min_prod"] = df_today.apply(lambda r: _mins(r.first_ticket, r.last_return), axis=1)
    df_today["prod_ratio"] = df_today["min_prod"] / df_today["min_total"] * 100
    prod_prod_min = df_today["min_prod"].sum(skipna=True)
    prod_total_min = df_today["min_total"].sum(skipna=True)
    prod_idle_min = prod_total_min - prod_prod_min

    # Totals/today
    fuel_L_today = df_today["fuel_used_L"].sum() if "fuel_used_L" in df_today else float("nan")
    distance_km_today = df_today["distance_km"].sum() if "distance_km" in df_today else float("nan")
    m3_today = df_today["load_volume_m3"].sum() if "load_volume_m3" in df_today else float("nan")
    avg_wait_min_today = _safe_mean(df_today["dur_waiting"]) if "dur_waiting" in df_today else float("nan")

    # Rolling 7-day utilization (sum cycle minutes / sum op minutes per truck per day)
    util_week = float("nan")
    if not df_week.empty:
        # trucks per day
        daily_trucks = df_week.groupby(df_week["date"])["truck"].nunique()
        total_op_min = (daily_trucks * op_minutes).sum()
        total_cycle = df_week["cycle_time"].sum()
        util_week = (total_cycle / total_op_min * 100) if total_op_min else float("nan")

    return {
        "df": df,
        "df_today": df_today,
        "df_yesterday": df_yesterday,
        "df_week": df_week,
        "df_48h": df_48h,

        "loads_today": int(len(df_today)),
        "loads_yesterday": int(len(df_yesterday)),
        "utilization_pct": float(utilization_today) if pd.notna(utilization_today) else float("nan"),
        "utilization_7d_pct": float(util_week) if pd.notna(util_week) else float("nan"),
        "avg_wait_min": float(avg_wait_min_today) if pd.notna(avg_wait_min_today) else float("nan"),
        "n_trucks": int(n_trucks_today),

        "prod_ratio": float(_safe_mean(df_today["prod_ratio"])) if not df_today.empty else float("nan"),
        "prod_prod_min": float(prod_prod_min) if pd.notna(prod_prod_min) else float("nan"),
        "prod_idle_min": float(prod_idle_min) if pd.notna(prod_idle_min) else float("nan"),

        "fuel_L_today": float(fuel_L_today) if pd.notna(fuel_L_today) else float("nan"),
        "distance_km_today": float(distance_km_today) if pd.notna(distance_km_today) else float("nan"),
        "m3_today": float(m3_today) if pd.notna(m3_today) else float("nan"),
    }


# -------------------------
# Intent Rules covering all suggestions
# -------------------------
def handle_simple_prompt(prompt: str, kpis: dict) -> str | None:
    p = (prompt or "").lower()
    df = kpis["df"]
    df_today = kpis["df_today"]
    df_yesterday = kpis["df_yesterday"]
    df_week = kpis["df_week"]
    df_48h = kpis["df_48h"]

    # 1) Volume today vs yesterday
    if "volume" in p and "today" in p and "yesterday" in p:
        v_t = df_today["load_volume_m3"].sum()
        v_y = df_yesterday["load_volume_m3"].sum()
        delta = v_t - v_y
        sign = "▲" if delta >= 0 else "▼"
        return f"Delivered volume — today: **{v_t:.1f} m³**, yesterday: **{v_y:.1f} m³** ({sign} **{delta:+.1f} m³**)."

    # 2) Driver most water this week
    if "driver" in p and "most water" in p:
        top = df_week.groupby("driver")["water_added_L"].sum().sort_values(ascending=False)
        if top.empty:
            return "No water addition records this week."
        return f"Top water addition this week: **{top.index[0]}** with **{top.iloc[0]:.1f} L**."

    # 3) Top three jobs longest wait last 48h
    if "longest wait" in p or ("top three" in p and "wait" in p):
        if "dur_waiting" not in df_48h:
            return "No waiting-time data available."
        top3 = df_48h.sort_values("dur_waiting", ascending=False).head(3)[["job_site", "dur_waiting"]]
        if top3.empty:
            return "No loads in the last 48 hours."
        lines = [f"- {r.job_site}: **{int(r.dur_waiting)} min**" for _, r in top3.iterrows()]
        return "**Top 3 longest waits (last 48h):**\n" + "\n".join(lines)

    # 4) Utilization vs 85% benchmark past 7 days
    if "utilization" in p and ("7" in p or "past 7" in p or "week" in p or "benchmark" in p):
        bench = 85.0
        actual = kpis.get("utilization_7d_pct", float("nan"))
        if pd.isna(actual):
            return "Not enough data to compute 7-day utilization."
        delta = actual - bench
        status = "above" if delta >= 0 else "below"
        return f"7-day utilization: **{actual:.1f}%**, which is **{abs(delta):.1f}% {status}** the **{bench}%** benchmark."

    # 5) Stage causing biggest delay this week
    if "stage" in p and ("biggest" in p or "causing" in p or "delay" in p) and "week" in p:
        stage_cols = [c for c in df_week.columns if c.startswith("dur_")]
        if not stage_cols:
            return "No stage timing data available."
        means = df_week[stage_cols].mean(numeric_only=True).sort_values(ascending=False)
        best = means.index[0].replace("dur_", "").replace("_", " ")
        return f"The stage with the highest average duration this week is **{best}** (≈ **{means.iloc[0]:.1f} min**)."

    # 6) Fuel cost today at $X/L
    if "fuel" in p and "cost" in p:
        price = _price_from_text(p)
        if price is None:
            return "Include a price per litre (e.g., **$1.80/L**) to estimate today’s fuel cost."
        L = kpis.get("fuel_L_today", float("nan"))
        if pd.isna(L):
            return "No fuel usage for today."
        return f"Fuel used today: **{L:,.1f} L** × **${price:.2f}/L** ≈ **${L*price:,.2f}**."

    # 7) Most efficient driver by m³/hr today
    if "efficient driver" in p or ("m³" in p and "/ hr" in p and "today" in p):
        grp = df_today.groupby("driver").apply(lambda g: g["load_volume_m3"].sum() / (g["cycle_time"].sum() / 60))
        if grp.empty:
            return "No driver data for today."
        top = grp.sort_values(ascending=False).head(1)
        return f"Most efficient driver today: **{top.index[0]}** at **{top.iloc[0]:.2f} m³/hr**."

    # 8) Drum RPM outliers this week
    if "rpm" in p or "drum" in p:
        if "drum_rpm" not in df_week:
            return "No drum RPM data available."
        low = df_week[df_week["drum_rpm"] < 4.0]
        high = df_week[df_week["drum_rpm"] > 6.5]
        return (
            f"Drum RPM outliers this week:\n"
            f"- Low (< 4): **{len(low)}** loads\n"
            f"- High (> 6.5): **{len(high)}** loads"
        )

    # 9) Breakdown of average cycle time per plant this week
    if "cycle time" in p and "plant" in p:
        tbl = df_week.groupby("origin_plant")["cycle_time"].mean().sort_values()
        lines = [f"- {idx}: **{val:.1f} min**" for idx, val in tbl.items()]
        return "**Avg cycle time by plant (week):**\n" + "\n".join(lines)

    # 10) Projects exceeded target m³/load (target 9.5)
    if "target" in p and "m³ / load" in p:
        target = 9.5
        tbl = df_week.groupby("project")["load_volume_m3"].mean()
        winners = tbl[tbl > target]
        if winners.empty:
            return f"No projects exceeded **{target} m³/load** this week."
        lines = [f"- {idx}: **{val:.2f} m³/load**" for idx, val in winners.sort_values(ascending=False).items()]
        return f"Projects above **{target} m³/load** this week:\n" + "\n".join(lines)

    # 11) Compare today wait to 7-day avg
    if "compare" in p and "wait" in p:
        today_w = _safe_mean(df_today["dur_waiting"]) if "dur_waiting" in df_today else float("nan")
        week_w = _safe_mean(df_week["dur_waiting"])  if "dur_waiting" in df_week  else float("nan")
        if pd.isna(today_w) or pd.isna(week_w):
            return "Waiting-time data not available."
        delta = today_w - week_w
        word = "higher" if delta > 0 else "lower"
        return f"Today’s avg wait: **{today_w:.1f} min**, 7-day avg: **{week_w:.1f} min** (**{abs(delta):.1f} min {word}**)."

    # 12) Jobs distance > 40 km + tips
    if "distance" in p and ("> 40" in p or "greater than 40" in p):
        long = df_week[df_week["distance_km"] > 40][["job_site", "distance_km"]]
        if long.empty:
            return "No jobs over 40 km this week."
        preview = long.sort_values("distance_km", ascending=False).head(10)
        lines = [f"- {r.job_site}: **{r.distance_km:.1f} km**" for _, r in preview.iterrows()]
        return (
            "**Jobs > 40 km (week):**\n" + "\n".join(lines) +
            "\n\nRouting tip: cluster deliveries, check closest plant, and align departure windows to avoid peak traffic."
        )

    # 13) Loads with water added > 120 L this week
    if "water" in p and ("> 120" in p or "greater than 120" in p):
        hot = df_week[df_week["water_added_L"] > 120][["ticket_id", "driver", "water_added_L", "project"]]
        if hot.empty:
            return "No loads exceeded 120 L of added water this week."
        lines = [f"- {r.ticket_id} ({r.driver}) – **{r.water_added_L:.0f} L** on *{r.project}*" for _, r in hot.head(10).iterrows()]
        return "**Loads with water added > 120 L (week):**\n" + "\n".join(lines)

    # 14) Predict tomorrow loads as 7-day average
    if "predict" in p and "tomorrow" in p:
        daily = df_week.groupby("date")["ticket_id"].count()
        if daily.empty:
            return "No data to forecast tomorrow’s loads."
        pred = daily.mean()
        return f"Based on the last 7 days, expected loads tomorrow ≈ **{pred:.0f}**."

    # 15) Hours today with worst wait times
    if ("hours" in p or "hour" in p) and "wait" in p and "today" in p:
        if "dur_waiting" not in df_today:
            return "No waiting-time data today."
        by_hour = df_today.groupby("hour")["dur_waiting"].mean().sort_values(ascending=False).head(3)
        lines = [f"- {int(h):02d}:00 → **{v:.1f} min**" for h, v in by_hour.items()]
        return "**Worst wait hours (today):**\n" + "\n".join(lines)

    # 16) Site with most total waiting time this week
    if "site" in p and "waiting" in p and "week" in p:
        if "dur_waiting" not in df_week:
            return "No waiting-time data for the week."
        agg = df_week.groupby("job_site")["dur_waiting"].sum().sort_values(ascending=False)
        if agg.empty:
            return "No site data available."
        return f"Site with most total waiting this week: **{agg.index[0]}** (≈ **{agg.iloc[0]:.0f} min**)."

    # 17) CO2 emissions today (diesel default; gasoline if mentioned)
    if ("co2" in p or "emission" in p) and "today" in p:
        L = kpis.get("fuel_L_today", float("nan"))
        if pd.isna(L) or L <= 0:
            return "No fuel usage for today, so CO₂ can’t be computed."
        fuel_type = "gasoline" if any(w in p for w in ["gasoline", "petrol"]) else os.getenv("COACH_DEFAULT_FUEL", "diesel").lower()
        factor = 2.31 if fuel_type == "gasoline" else 2.68
        kg = L * factor
        t = kg / 1000.0
        return f"CO₂ today using **{fuel_type}**: **{kg:,.0f} kg** (≈ **{t:.3f} t**) from **{L:,.1f} L**."

    # 18) Empirical best-practice cycle for ~30 km (use data window 27–33 km)
    if "best" in p and "30 km" in p and "cycle" in p:
        window = df_week[(df_week["distance_km"] >= 27) & (df_week["distance_km"] <= 33)]
        if window.empty:
            avg = df_week["cycle_time"].mean()
            return f"No 30 km window loads this week; overall avg cycle = **{avg:.1f} min**."
        return f"Empirical cycle time for ~30 km (27–33 km) = **{window['cycle_time'].mean():.1f} min**."

    # 19) Hydraulic pressure extremes this week
    if "hydraulic" in p or ("pressure" in p and "week" in p):
        if "hydraulic_pressure" not in df_week:
            return "No hydraulic pressure data available."
        low = df_week[df_week["hydraulic_pressure"] < 1850]
        high = df_week[df_week["hydraulic_pressure"] > 2150]
        return f"Pressure extremes this week: low (<1850): **{len(low)}** loads; high (>2150): **{len(high)}** loads."

    # 20) 5 slowest washout times this week
    if "washout" in p or ("wash" in p and "slow" in p):
        col = "washout_duration_min" if "washout_duration_min" in df_week else "dur_washing"
        if col not in df_week:
            return "No washout duration data available."
        slow = df_week.sort_values(col, ascending=False).head(5)[["ticket_id", "driver", col]]
        lines = [f"- {r.ticket_id} ({r.driver}) – **{getattr(r, col):.1f} min**" for _, r in slow.iterrows()]
        return "**5 slowest washouts (week):**\n" + "\n".join(lines)

    # 21) Top 3 cost-saving opportunities this week (data-driven heuristics)
    if "cost" in p and "opportunit" in p:
        # Heuristic estimates
        loads = len(df_week)
        avg_wait = _safe_mean(df_week["dur_waiting"]) if "dur_waiting" in df_week else 0
        avg_dist = _safe_mean(df_week["distance_km"]) if "distance_km" in df_week else 0
        fuel_L = df_week["fuel_used_L"].sum() if "fuel_used_L" in df_week else 0

        # Assumptions
        hourly_rate = float(os.getenv("COACH_RATE_PER_HOUR", "45"))  # $/hr
        fuel_price = float(os.getenv("COACH_FUEL_PRICE", "1.80"))    # $/L

        save_wait_min = 3.0  # target cut
        save_wait_cost = (save_wait_min / 60) * hourly_rate * loads

        # 2% routing improvement on distance & fuel
        route_gain_km = 0.02 * df_week["distance_km"].sum() if "distance_km" in df_week else 0
        route_gain_fuel_cost = 0.02 * fuel_L * fuel_price

        # RPM normalization – assume 1% fuel reduction if >6.5 or <4 exist
        rpm_outliers = 0
        if "drum_rpm" in df_week:
            rpm_outliers = len(df_week[(df_week["drum_rpm"] < 4.0) | (df_week["drum_rpm"] > 6.5)])
        rpm_gain_cost = 0.01 * fuel_L * fuel_price if rpm_outliers > 0 else 0

        lines = [
            f"1) Cut wait by 3 min/load → ≈ **${save_wait_cost:,.0f}** /week saved.",
            f"2) Improve routing by 2% → ≈ **{route_gain_km:,.0f} km** & **${route_gain_fuel_cost:,.0f}** fuel saved.",
            f"3) Normalize RPM (fix {rpm_outliers} outliers) → ≈ **${rpm_gain_cost:,.0f}** fuel saved.",
        ]
        return "**Top 3 cost-saving opportunities (week):**\n" + "\n".join(lines)

    # 22) Driver consistently beats m³/hr benchmark ≥ 3.5 this week
    if "consistently" in p and "m³ / hr" in p:
        bench = 3.5
        perf = df_week.groupby("driver").apply(lambda g: g["load_volume_m3"].sum() / (g["cycle_time"].sum() / 60))
        winners = perf[perf >= bench].sort_values(ascending=False)
        if winners.empty:
            return f"No drivers met the **{bench} m³/hr** benchmark this week."
        lines = [f"- {idx}: **{val:.2f} m³/hr**" for idx, val in winners.items()]
        return f"Drivers ≥ **{bench} m³/hr** (week):\n" + "\n".join(lines)

    # 23) Rank plants by average cycle time this week
    if "rank" in p and "plant" in p and "cycle" in p:
        tbl = df_week.groupby("origin_plant")["cycle_time"].mean().sort_values()
        lines = [f"{i+1}. {idx}: **{val:.1f} min**" for i, (idx, val) in enumerate(tbl.items())]
        return "**Plants by avg cycle (best → worst):**\n" + "\n".join(lines)

    # 24) Days when fuel L/km > 0.55 this week
    if "fuel" in p and "/ km" in p:
        if not {"fuel_used_L", "distance_km"}.issubset(df_week.columns):
            return "Missing fuel/distance data."
        daily = df_week.assign(l_per_km=df_week["fuel_used_L"] / df_week["distance_km"])
        flag = daily.groupby("date")["l_per_km"].mean()
        hot = flag[flag > 0.55]
        if hot.empty:
            return "No days exceeded **0.55 L/km** this week."
        lines = [f"- {str(d)}: **{v:.2f} L/km**" for d, v in hot.items()]
        return "**Days > 0.55 L/km (week):**\n" + "\n".join(lines)

    # 25) Quick wins to boost utilization above 88 %
    if "quick wins" in p or ("boost" in p and "utilization" in p):
        util_today = kpis.get("utilization_pct", float("nan"))
        loads_today = kpis.get("loads_today", 0)
        tips = [
            "Shorten loading to <7 min (prep tickets, pre-stage aggregates).",
            "Pre-call sites 20 min before arrival to minimize gate delays.",
            "Schedule washout windows to avoid peak return congestion.",
        ]
        lead = f"Utilization today: **{util_today:.1f}%**. To move toward **88%+**:"
        lines = [f"- {t}" for t in tips]
        return lead + "\n" + "\n".join(lines)

    # --- Common extras for completeness ---

    # Simple: loads today
    if "loads" in p and "today" in p:
        return f"Loads delivered today: **{kpis.get('loads_today', 0)}**."

    # Simple: avg wait today
    if "average wait" in p or "avg wait" in p:
        w = kpis.get("avg_wait_min", float("nan"))
        if pd.isna(w):
            return "No waiting-time data."
        return f"Average wait today is **{w:.1f} min**."

    # Fallback
    return None
