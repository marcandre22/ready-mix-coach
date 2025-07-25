import pandas as pd
import random
from datetime import datetime, timedelta

def load_data(n_jobs: int = 50):
    drivers = ["Marc", "Julie", "Antoine", "Sarah", "Luc", "Melanie", "Simon", "Elise"]
    plants  = ["Montreal", "Laval", "Quebec", "Drummondville"]
    sites   = ["Longueuil", "Trois‑Rivieres", "Sherbrooke", "Repentigny"]

    rows = []
    base_time = datetime(2025, 7, 15, 5, 0)

    for i in range(n_jobs):
        start = base_time + timedelta(minutes=random.randint(0, 600))
        durs = [random.randint(8, 20), random.randint(4, 9), random.randint(12, 35),
                random.randint(3, 15), random.randint(8, 18), random.randint(4, 9), random.randint(8, 22)]

        water_added = round(random.uniform(0, 120),1)
        rpm = random.randint(3, 15)
        pressure = random.randint(300, 1200)
        fuel_used = round(random.uniform(8, 30),1)
        avg_speed = round(random.uniform(35, 65),1)

        row = {
            "job_id": f"J{1000+i}",
            "driver": random.choice(drivers),
            "origin_plant": random.choice(plants),
            "job_site": random.choice(sites),
            "start_time": start.strftime("%Y-%m-%d %H:%M"),
            "cycle_time": sum(durs),
            "water_added_L": water_added,
            "drum_rpm": rpm,
            "hyd_press_PSI": pressure,
            "fuel_L": fuel_used,
            "avg_speed_kmh": avg_speed,
        }
        for name, dur in zip(["dispatch", "loaded", "en_route", "waiting", "discharging", "washing", "back"], durs):
            row[f"dur_{name}"] = dur
        rows.append(row)
    return pd.DataFrame(rows)
