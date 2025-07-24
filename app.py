# app.py
import streamlit as st
from openai import OpenAI
import pandas as pd, random
from datetime import datetime
from kb.knowledge import BEST_PRACTICE
from prompts.tone import get_tone
from prompts.samples import SAMPLE_QUESTIONS

st.set_page_config(page_title="Ready-Mix Coach", layout="wide")
st.markdown("""
<style>
body {background:#121212; color:#f1f1f1;}
.main {background:#121212;}
h1,h2 {color:#E7662E;}
.stButton>button {background:#E7662E; color:white; font-weight:bold;}
</style>""", unsafe_allow_html=True)

st.title("CDWARE Ready-Mix Coach")

# ---------- Simulated data ----------
@st.cache_data
def load_data(n=50):
    drivers = ["Marc","Julie","Antoine","Sarah","Luc","Melanie","Simon","Elise"]
    plants  = ["Montreal","Laval","Quebec","Drummondville"]
    sites   = ["Longueuil","Trois-Rivieres","Sherbrooke","Repentigny"]
    rows=[]
    for i in range(n):
        durs=[random.randint(10,25),random.randint(5,10),random.randint(15,30),
              random.randint(5,20),random.randint(10,20),random.randint(5,10),random.randint(10,25)]
        rows.append({
            "job_id":f"J{1000+i}",
            "driver":random.choice(drivers),
            "origin_plant":random.choice(plants),
            "job_site":random.choice(sites),
            "cycle_time":sum(durs),
            "water_added_L":round(random.uniform(0,120),1),
            **{f"dur_{s}":v for s,v in zip(
                ["dispatch","loaded","en_route","waiting","discharging","washing","back"], durs)}
        })
    return pd.DataFrame(rows)

df = load_data()

# ---------- Prompt builder ----------
def build_prompt(question:str)->str:
    kpis = "\n".join(
        f"- Avg {c.replace('dur_','').title()}: {v:.1f} min"
        for c,v in df.filter(like="dur_").mean().items()
    )
    water_tot = df.groupby("driver")["water_added_L"].sum().sort_values(ascending=False).head(5)
    water_lines = "\n".join([f"  • {d}: {w:.1f} L" for d,w in water_tot.items()])

    return f"""
You are an expert ready-mix dispatch coach.

Snapshot KPIs
Jobs: {len(df)} | Avg cycle: {df['cycle_time'].mean():.1f} min
{kpis}

Top drivers by water added
{water_lines}

Internal notes (never quote):
{BEST_PRACTICE}

{get_tone()}

Question: {question}
""".strip()

# ---------- Chat UI ----------
default_q = random.choice(SAMPLE_QUESTIONS)
st.text_input("Suggestion", value=default_q, disabled=True)
user_q = st.text_input("Ask the coach:")
if user_q:
    with st.spinner("Thinking…"):
        client = OpenAI()
        out = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":build_prompt(user_q)}]
        )
        st.markdown(out.choices[0].message.content)

# ---------- Export ----------
if st.button("Export CSV"):
    st.download_button("Download", df.to_csv(index=False), "ready_mix.csv")
