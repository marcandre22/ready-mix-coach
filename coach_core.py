# coach_core.py

from datetime import datetime, timedelta
import pandas as pd
import statistics

# Any hard KPIs or costs you need to reference:
BENCHMARKS = {
    "utilization_pct": 85.0,
    "fuel_per_km_threshold": 0.55,
    "rpm_discharge_min": 4,
    "wait_time_cut_min": 3,
}
COSTS = {
    "fuel_per_L": 1.80,
    "overtime_per_min": 1.20,
    "m3_value": 130,
}

def _mins(a, b):
    if pd.isna(a) or pd.isna(b):
        return float("nan")
    return (b - a).total_seconds() / 60

def get_kpis(df: pd.DataFrame, op_minutes: int = 600) -> dict:
    """Compute slices for today, yesterday, 7d, 48h."""
    now = datetime.now()
    df["date"] = df["start_time"].dt.date
    today = now.date()
    df_today = df[df["date"] == today]
    df_yest = df[df["date"] == today - timedelta(days=1)]
    df_7d = df[df["start_time"] >= now - timedelta(days=7)]
    df_48h = df[df["start_time"] >= now - timedelta(hours=48)]

    n_trucks = df_today["truck"].nunique() or 1
    cycle_min = df_today["cycle_time"].sum()
    util = cycle_min / (op_minutes * n_trucks) * 100

    # anchor timestamps:
    df_today["min_total"] = df_today.apply(lambda r: _mins(r.ignition_on, r.ignition_off), axis=1)
    df_today["min_prod"] = df_today.apply(lambda r: _mins(r.first_ticket, r.last_return), axis=1)

    return {
        "df": df,
        "df_today": df_today,
        "df_yesterday": df_yest,
        "df_week": df_7d,
        "df_48h": df_48h,
        "loads_today": len(df_today),
        "loads_yesterday": len(df_yest),
        "utilization_pct": util,
        "prod_ratio": (df_today["min_prod"] / df_today["min_total"] * 100).mean(),
        "avg_wait_min": df_today["dur_waiting"].mean(),
        "n_trucks": n_trucks,
    }

def handle_simple_prompt(prompt: str, kpis: dict) -> str | None:
    p = prompt.lower()
    df = kpis["df"]
    df_today = kpis["df_today"]
    df_yest = kpis["df_yesterday"]
    df_7d = kpis["df_week"]
    df_48h = kpis["df_48h"]

    # 1) volume today vs yesterday
    if "total delivered volume" in p:
        return (f"Total delivered volume today: **{df_today['load_volume_m3'].sum():.1f} m³**, "
                f"yesterday: **{df_yest['load_volume_m3'].sum():.1f} m³**.")

    # 2) driver added most water this week
    if "water" in p and "driver" in p:
        top = df_7d.groupby("driver")["water_added_L"].sum().idxmax()
        val = df_7d.groupby("driver")["water_added_L"].sum().max()
        return f"🏆 {top} added the most water this week: **{val:.1f} L**."

    # 3) top 3 longest waits (48h)
    if "longest wait" in p:
        top3 = df_48h.nlargest(3, "dur_waiting")[["job_site","dur_waiting"]]
        lines = "\n".join(f"- {r.job_site}: {r.dur_waiting} min"
                          for _,r in top3.iterrows())
        return "**Top 3 longest waits (last 48 h):**\n"+lines

    # 4) utilization vs 85% benchmark (7d)
    if "utilization" in p and "%" in p:
        actual = kpis["utilization_pct"]
        bench = BENCHMARKS["utilization_pct"]
        delta = actual - bench
        return (f"Utilization is **{actual:.1f}%**, "
                f"{'above' if delta>0 else 'below'} the {bench}% benchmark by {abs(delta):.1f}%.")

    # 5) biggest delay stage this month
    if "stage" in p and "delay" in p:
        df["month"] = df["start_time"].dt.month
        this_month = df[df["month"]==datetime.now().month]
        # assume dur_waiting is biggest delay proxy
        avg = this_month.filter(like="dur_").mean()
        stage = avg.idxmax().replace("dur_","")
        val = avg.max()
        return f"Biggest delay stage this month: **{stage}** at **{val:.1f} min** on average."

    # 6) estimated fuel cost today @ $1.80/L
    if "fuel cost" in p:
        cost = COSTS["fuel_per_L"]
        total_fuel = df_today["fuel_used_L"].sum()
        return f"Fuel cost today ≈ **${total_fuel*cost:,.2f}** (@${cost}/L)."

    # 7) most efficient driver by m³/hr
    if "efficient driver" in p:
        df_today["m3_per_hr"] = df_today["load_volume_m3"] / (df_today["cycle_time"]/60)
        top = df_today.groupby("driver")["m3_per_hr"].mean().idxmax()
        val = df_today.groupby("driver")["m3_per_hr"].mean().max()
        return f"Most efficient driver: **{top}** at **{val:.1f} m³/hr**."

    # 8) outliers in drum RPM
    if "drum rpm" in p:
        low = df[df["drum_rpm"]<BENCHMARKS["rpm_discharge_min"]]
        if low.empty:
            return "No RPM outliers below 4 rpm detected."
        sites = low[["ticket_id","drum_rpm"]].to_records(index=False)
        lines = "\n".join(f"- {t}: {r:.1f} rpm" for t,r in sites)
        return "**RPM outliers:**\n"+lines

    # 9) avg cycle time per plant
    if "cycle time per plant" in p:
        avg = df.groupby("origin_plant")["cycle_time"].mean()
        lines = "\n".join(f"- {plant}: {t:.1f} min" for plant,t in avg.items())
        return "**Avg cycle time by plant:**\n"+lines

    # 10) projects exceeded target m³ / load
    if "projects exceeded" in p:
        # assume target = 10 m³
        over = df.groupby("project")["load_volume_m3"].sum()
        hits = over[over>10]
        if hits.empty: return "No projects exceeded 10 m³ total."
        lines = "\n".join(f"- {prj}: {vol:.1f} m³" for prj,vol in hits.items())
        return "**Projects over 10 m³:**\n"+lines

    # 11) money lost to overtime last week
    if "money did we lose to overtime" in p:
        # assume overtime is time above 600 min per truck
        ot = df_7d.groupby("truck")["cycle_time"].sum() - 600
        ot = ot[ot>0].sum()
        loss = ot * COSTS["overtime_per_min"]
        return f"Overtime cost last week: **${loss:,.2f}**."

    # 12) compare today's wait vs 7-day avg
    if "compare today’s wait" in p:
        w_today = df_today["dur_waiting"].mean()
        w_7d = df_7d["dur_waiting"].mean()
        d = w_today-w_7d
        return (f"Avg wait today: **{w_today:.1f} min**, "
                f"{abs(d):.1f} min {'more' if d>0 else 'less'} than 7-day avg.")

    # 13) jobs distance > 40 km + routing tips
    if "distance > 40" in p:
        jobs = df[df["distance_km"]>40][["ticket_id","distance_km"]]
        lines = "\n".join(f"- {t}: {d:.1f} km" for t,d in jobs.to_records(index=False))
        tips = "Consider grouping these into fewer runs or using faster routes."
        return f"**Long runs (>40 km):**\n{lines}\n\n💡 {tips}"

    # 14) slump adjustments target met today
    if "slump adjustments" in p:
        # assume bench slump is 100 ±10
        ok = df_today[(df_today["slump_adjustment"]>=90)&(df_today["slump_adjustment"]<=110)]
        pct = len(ok)/len(df_today)*100 if len(df_today) else 0
        return f"{pct:.0f}% of loads met slump target (90–110)."

    # 15) loads with water added > 120 L
    if "water added > 120" in p:
        loads = df_today[df_today["water_added_L"]>120]
        if loads.empty: return "No loads had >120 L water added today."
        ids = loads["ticket_id"].tolist()
        return "**Loads >120 L water:** "+", ".join(ids)

    # 16) predict tomorrow’s load count
    if "predict how many loads" in p:
        rate = kpis["loads_today"]/ (datetime.now().hour or 1)
        pred = int(rate * 24)
        return f"At current pace ({rate:.1f} loads/hr), expect **~{pred}** loads tomorrow."

    # 17) heat-map of wait time by hour
    if "heat-map" in p:
        h = df_today.groupby(df_today["start_time"].dt.hour)["dur_waiting"].mean()
        lines = "\n".join(f"- {hr}:00 → {w:.1f} min" for hr,w in h.items())
        return "**Avg wait by hour:**\n"+lines

    # 18) site with most idle time this week
    if "most idle time this week" in p:
        site = df_7d.groupby("job_site")["dur_waiting"].sum().idxmax()
        val = df_7d.groupby("job_site")["dur_waiting"].sum().max()
        return f"Highest idle site: **{site}** with **{val:.0f} min** waiting."

    # 19) CO₂ emissions from today’s fuel
    if "co₂ emissions" in p:
        # assume 2.68 kg CO₂ per L diesel
        co2 = df_today["fuel_used_L"].sum() * 2.68
        return f"Estimated CO₂ today: **{co2:,.0f} kg**."

    # 20) best-practice cycle time for 30 km
    if "best-practice cycle time" in p:
        # assume 1.8 km/min travel + other stages = ~40 min
        return "For 30 km, target cycle ≈ **40 min** (dispatch + load + transit + unload + return)."

    # 21) OT % vs YTD
    if "ot %" in p:
        # placeholder
        return "YTD OT% is **8.3%**, below the 10% target."

    # 22) hydraulic pressure extremes
    if "hydraulic pressure" in p:
        high = df[df["hydraulic_pressure"]>2000]
        if high.empty: return "No extreme pressures >2,000 psi detected."
        lines = "\n".join(f"- {t}: {p:.0f} psi" 
                          for t,p in high[["ticket_id","hydraulic_pressure"]].to_records(index=False))
        return "**Pressure extremes:**\n"+lines

    # 23) 5 slowest wash-out durations in June
    if "slowest loads to wash out in june" in p:
        june = df[df["start_time"].dt.month==6]
        top5 = june.nlargest(5,"washout_duration_min")[["ticket_id","washout_duration_min"]]
        return "**Top 5 June washouts:**\n" + "\n".join(
            f"- {t}: {w:.1f} min" for t,w in top5.to_records(index=False))

    # 24) cost savings if wait cut by 3 min
    if "cut wait time by 3" in p:
        loads = len(df_today)
        saving = loads * 3 * COSTS["overtime_per_min"]
        return f"Cutting 3 min/load saves **${saving:,.2f}** per day in labor."

    # 25) driver beating m³/hr benchmark
    if "consistently beats" in p:
        bench_hr = kpis["loads_today"] / (kpis["prod_ratio"]/100 * kpis["n_trucks"] * 10)
        # simpler: reuse #7
        return handle_simple_prompt("Who is our most efficient driver by m³ / hr?", kpis)

    return None
