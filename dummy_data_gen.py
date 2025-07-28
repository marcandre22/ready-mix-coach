# dummy_data_gen.py – v2 with productivity timestamps
# -------------------------------------------------------------
# Generates realistic ready‑mix delivery tickets + productivity anchors
# • Multi‑day history  (days_back)
# • Multiple jobs per day (n_jobs_per_day)
# • Adds ignition_on, first_ticket, last_return, ignition_off timestamps
# -------------------------------------------------------------

import streamlit as st                    # for @st.cache_data
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

_DRIVERS = ["Marc", "Julie", "Antoine", "Sarah",
            "Luc", "Melanie", "Simon", "Elise"]


def _haversine(p, s):
    R = 6371.0
    lat1, lon1 = radians(p[0]), radians(p[1])
    lat2, lon2 = radians(s[0]), radians(s[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c


@st.cache_data
def load_data(*, days_back: int = 3, n_jobs_per_day: int = 60) -> pd.DataFrame:
    """Return a DataFrame of simulated tickets spanning `days_back` days."""

    rows = []
    ticket_id = 10_000
    base = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)

    for d in range(days_back):
        day_start = base - timedelta(days=d)
        for _ in range(n_jobs_per_day):
            # --- core timings ------------------------------------------------
            start = day_start + timedelta(minutes=random.randint(0, 12*60))
            plant   = random.choice(list(_PLANTS))
            site    = random.choice(list(_SITES))
            dist_km = round(_haversine(_PLANTS[plant], _SITES[site]), 1)

            # stage durations (min)
            d_dispatch   = random.randint(8, 20)
            d_loaded     = random.randint(4, 9)
            d_en_route   = max(5, int(dist_km/1.8))
            d_waiting    = random.randint(3, 15)
            d_disch      = random.randint(8, 18)
            d_wash       = random.randint(4, 9)
            d_back       = d_en_route  # same as outbound for simplicity
            durs = [d_dispatch,d_loaded,d_en_route,
                    d_waiting,d_disch,d_wash,d_back]

            fuel_L  = round(dist_km * random.uniform(0.35, 0.55), 1)
            water_L = round(random.uniform(50, 150), 1)

            # --- productivity anchors --------------------------------------
            ignition_on   = start - timedelta(minutes=random.randint(20, 40))
            first_ticket  = start                    # A -> B gap = load dispatch
            last_return   = start + timedelta(minutes=sum(durs[:-1]))  # before wash/back counted
            ignition_off  = last_return + timedelta(minutes=random.randint(10, 30))

            row = {
                "ticket_id":   f"T{ticket_id}",
                "truck":       random.randint(100, 120),
                "driver":      random.choice(_DRIVERS),
                "origin_plant":plant,
                "job_site":    site,
                "start_time":  start,
                "cycle_time":  sum(durs),
                "distance_km": dist_km,
                "fuel_used_L": fuel_L,
                "water_added_L": water_L,
                "load_volume_m3": 10,
                # productivity timestamps
                "ignition_on":  ignition_on,
                "first_ticket": first_ticket,
                "last_return":  last_return,
                "ignition_off": ignition_off,
            }
            stages = ["dispatch","loaded","en_route","waiting",
                      "discharging","washing","back"]
            for s,v in zip(stages, durs):
                row[f"dur_{s}"] = v

            rows.append(row)
            ticket_id += 1

    df = pd.DataFrame(rows)
    return df
