# dummy_data_gen.py – generates updated telematics dataset
import pandas as pd
import random
from datetime import datetime, timedelta

@st.cache_data
def load_data(n_projects: int = 3):
    drivers = ["Marc", "Julie", "Antoine", "Sarah", "Luc", "Melanie", "Simon", "Elise"]
    plants = ["Montreal", "Laval", "Quebec", "Drummondville"]
    job_sites = ["Longueuil", "Trois-Rivieres", "Sherbrooke", "Repentigny"]
    mix_type = "32 MPa 14mm Mix 5-8% Air"

    site_distances_km = {
        ("Montreal", "Longueuil"): 12,
        ("Montreal", "Trois-Rivieres"): 140,
        ("Montreal", "Sherbrooke"): 155,
        ("Montreal", "Repentigny"): 36,
        ("Laval", "Longueuil"): 28,
        ("Laval", "Trois-Rivieres"): 130,
        ("Laval", "Sherbrooke"): 145,
        ("Laval", "Repentigny"): 30,
        ("Quebec", "Longueuil"): 240,
        ("Quebec", "Trois-Rivieres"): 130,
        ("Quebec", "Sherbrooke"): 230,
        ("Quebec", "Repentigny"): 210,
        ("Drummondville", "Longueuil"): 105,
        ("Drummondville", "Trois-Rivieres"): 85,
        ("Drummondville", "Sherbrooke"): 70,
        ("Drummondville", "Repentigny"): 95
    }

    rows = []
    job_id_base = 1000
    ticket_id_base = 5000
    base_time = datetime(2025, 7, 15, 5, 0)

    for p in range(n_projects):
        project_name = f"Project {chr(65+p)}"
        total_volume = random.randint(80, 150)
        load_volume = 10
        num_loads = total_volume // load_volume

        for l in range(num_loads):
            start_time = base_time + timedelta(minutes=random.randint(0, 600))
            origin = random.choice(plants)
            site = random.choice(job_sites)
            distance_km = site_distances_km.get((origin, site), random.randint(10, 200))

            d_dispatch = random.randint(8, 20)
            d_loaded = random.randint(4, 9)
            d_en_route = random.randint(12, 35)
            d_waiting = random.randint(3, 15)
            d_disch = random.randint(8, 18)
            d_wash = random.randint(4, 9)
            d_back = random.randint(8, 22)
            durs = [d_dispatch, d_loaded, d_en_route, d_waiting, d_disch, d_wash, d_back]

            fuel_rate = random.uniform(0.35, 0.55)  # L/km
            fuel_used = round(distance_km * fuel_rate, 1)

            row = {
                "project": project_name,
                "job_id": f"J{job_id_base + p}",
                "ticket_id": f"T{ticket_id_base + l + (p * num_loads)}",
                "driver": random.choice(drivers),
                "origin_plant": origin,
                "job_site": site,
                "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
                "cycle_time": sum(durs),
                "dur_dispatch": d_dispatch,
                "dur_loaded": d_loaded,
                "dur_en_route": d_en_route,
                "dur_waiting": d_waiting,
                "dur_discharging": d_disch,
                "dur_washing": d_wash,
                "dur_back": d_back,
                "distance_km": distance_km,
                "fuel_used_L": fuel_used,
                "load_volume_m3": load_volume,
                "water_added_L": round(random.uniform(50, 150), 1),
                "drum_rpm": random.randint(3, 15),
                "mix": mix_type
            }
            rows.append(row)

    return pd.DataFrame(rows)
