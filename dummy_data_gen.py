# dummy_data_gen.py – deterministic dummy data with seed
import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
from math import sin, cos, sqrt, atan2, radians

_PLANTS = {
    "Montreal":       (45.550, -73.700),
    "Laval":          (45.610, -73.720),
    "Quebec":         (46.820, -71.220),
    "Drummondville":  (45.883, -72.470),
}

_SITES = {
    "Longueuil":      (45.530, -73.520),
    "Trois-Rivieres": (46.350, -72.560),
    "Sherbrooke":     (45.400, -71.900),
    "Repentigny":     (45.740, -73.470),
}

_DRIVERS = ["Marc", "Julie", "Antoine", "Sarah", "Luc", "Melanie", "Simon", "Elise"]
_PROJECTS = ["Tower A", "Metro Site", "Hospital Wing", "Airport Zone"]
_BENCH_SLUMP = 100

def _haversine(p, s):
    R = 6371.0
    lat1, lon1 = radians(p[0]), radians(p[1])
    lat2, lon2 = radians(s[0]), radians(s[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

@st.cache_data
def load_data(*, days_back: int = 7, n_jobs_per_day: int = 60, seed: int = 7) -> pd.DataFrame:
    random.seed(seed)  # <— deterministic
    rows = []
    ticket_id = 10000
    base = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)

    for d in range(days_back):
        day_start = base - timedelta(days=d)
        for _ in range(n_jobs_per_day):
            start = day_start + timedelta(minutes=random.randint(0, 12 * 60))
            plant = random.choice(list(_PLANTS))
            site = random.choice(list(_SITES))
            dist_km = round(_haversine(_PLANTS[plant], _SITES[site]), 1)

            # Stage durations
            d_dispatch = random.randint(8, 20)
            d_loaded = random.randint(4, 9)
            d_en_route = max(5, int(dist_km / 1.8))
            d_waiting = random.randint(3, 15)
            d_disch = random.randint(8, 18)
            d_wash = random.randint(4, 9)
            d_back = d_en_route
            durs = [d_dispatch, d_loaded, d_en_route, d_waiting, d_disch, d_wash, d_back]

            fuel_L = round(dist_km * random.uniform(0.35, 0.55), 1)
            water_L = round(random.uniform(50, 160), 1)
            rpm = random.uniform(3.0, 6.5)
            slump = _BENCH_SLUMP + random.randint(-10, 15)
            return_m3 = round(random.random() * 0.5, 2)
            pressure = round(random.uniform(1800, 2200), 1)
            washout = random.randint(5, 20)
            driver = random.choice(_DRIVERS)
            project = random.choice(_PROJECTS)
            eta_offset = random.randint(-20, 20)

            ignition_on = start - timedelta(minutes=random.randint(20, 40))
            first_ticket = start
            last_return = start + timedelta(minutes=sum(durs[:-1]))
            ignition_off = last_return + timedelta(minutes=random.randint(10, 30))
            actual_arrival = first_ticket + timedelta(minutes=d_dispatch + d_loaded + d_en_route)
            eta = actual_arrival - timedelta(minutes=eta_offset)

            row = {
                "ticket_id": f"T{ticket_id}",
                "truck": random.randint(100, 120),
                "driver": driver,
                "project": project,
                "origin_plant": plant,
                "job_site": site,
                "start_time": start,
                "cycle_time": sum(durs),
                "distance_km": dist_km,
                "fuel_used_L": fuel_L,
                "water_added_L": water_L,
                "drum_rpm": rpm,
                "slump_adjustment": slump,
                "return_volume_m3": return_m3,
                "hydraulic_pressure": pressure,
                "washout_duration_min": washout,
                "ETA": eta,
                "actual_arrival": actual_arrival,
                "load_volume_m3": 10,
                "ignition_on": ignition_on,
                "first_ticket": first_ticket,
                "last_return": last_return,
                "ignition_off": ignition_off,
            }

            stages = ["dispatch", "loaded", "en_route", "waiting", "discharging", "washing", "back"]
            for s, v in zip(stages, durs):
                row[f"dur_{s}"] = v

            rows.append(row)
            ticket_id += 1

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["start_time"]).dt.date  # handy for filtering & tools
    return df
