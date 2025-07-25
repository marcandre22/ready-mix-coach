# instruction_set.py – v2 (conversational + suggested prompts)
"""Defines how the coach should behave and offers a list of pre‑loaded questions
that the UI can surface to users (e.g., as quick‑tap suggestions).
"""

GUIDELINES = {
    "language": "English",
    "domain": "Ready-Mix Concrete Operations",
    # persona description gives the LLM a human‑like style
    "persona": (
        "You are a seasoned fleet‑dispatch mentor with a friendly, practical tone. "
        "Speak like a colleague on a job‑site walk‑through—clear, concise, and action‑oriented."
    ),
    "rules": [
        # Context & memory
        "Remember the last few user questions and your own answers; reuse that context instead of repeating it.",
        "If the follow‑up logically relates to the previous topic, answer directly. If it changes topic or lacks data, ask a short clarifying question first.",

        # Data handling
        "Use the dataset provided; cite concrete numbers (min, %, L, km, m³) when available.",
        "If a key figure (fuel price, hourly rate, etc.) is missing, ask for it before computing a result.",

        # Coaching style
        "Always give one to two actionable suggestions tied to the numbers and quantify likely impact (time, $ or CO₂).",
        "Close with an open question to deepen the analysis or confirm the action plan.",

        # Knowledge usage
        "Do not quote internal documents verbatim—paraphrase them.",
        "Expertise covers telematics, batching, QC, dispatch sequencing, and fuel‑cost optimisation."
    ],
}

# ------------------------------------------------------------------
# 50 Suggested prompts – can be rendered in the UI as quick actions
# ------------------------------------------------------------------
SUGGESTED_PROMPTS = [
    "What was our total delivered volume today vs. yesterday?",
    "Which driver added the most water this week?",
    "Show the top three jobs with the longest wait times in the last 48 hours.",
    "How does our utilization compare to the 85 % benchmark for the past 7 days?",
    "Which stage is causing the biggest delay this month?",
    "Estimate the fuel cost for today’s deliveries at $1.80 /L.",
    "Who is our most efficient driver by m³ / hr?",
    "Highlight any outliers in drum RPM that might indicate QC issues.",
    "Give me a breakdown of average cycle time per plant.",
    "Which projects exceeded the target m³ / load?",
    "How much money did we lose to overtime last week?",
    "Compare today’s wait time to our 7‑day rolling average.",
    "List jobs where distance > 40 km and suggest routing tips.",
    "Did we meet our target slump adjustments today?",
    "Identify any loads with water added > 120 L.",
    "Predict how many loads we’ll need tomorrow based on current pacing.",
    "Show a heat‑map of wait time by hour of day.",
    "Which site caused the most idle time this week?",
    "Calculate CO₂ emissions for today’s fuel usage.",
    "What’s the best‑practice cycle time for 30 km hauls?",
    "How does our OT % compare to benchmark year‑to‑date?",
    "Flag any jobs with hydraulic pressure extremes.",
    "Give me the 5 slowest loads to wash out in June.",
    "Estimate cost savings if we cut wait time by 3 min/load.",
    "Which driver consistently beats the m³ / hr benchmark?",
    "Summarise today’s KPI performance in one paragraph.",
    "Rank plants by average cycle time this quarter.",
    "How many cubic metres remain to finish Project Tower A?",
    "Identify days when fuel L / km exceeded 0.55.",
    "Recommend actions to reduce water addition variance.",
    "What’s our average utilisation on Saturdays?",
    "Generate an anomaly report for the past 24 hours.",
    "Compare driver John vs. Julie on cycle efficiency.",
    "How many loads had RPM < 4 during discharge?",
    "What is today’s delivery success rate within ±10 min of ETA?",
    "Calculate average travel speed by route segment.",
    "Show me the top 3 cost‑saving opportunities this month.",
    "Which driver had the shortest total waiting time last week?",
    "Evaluate our performance against 2016 KPI targets.",
    "Estimate concrete wasted due to returns in June.",
    "Provide a daily summary email of KPIs and outliers.",
    "If fuel rises to $2.10 /L, how does cost per m³ change?",
    "Find any jobs where cycle time > 170 min and explain why.",
    "Compare today’s m³ / load to the rolling 30‑day average.",
    "List projects with more than 10 loads delivered so far.",
    "Identify trends in wait time by weekday.",
    "Recommend benchmark updates based on the last 90 days of data.",
    "How much overtime did driver Sarah accrue this pay period?",
    "Generate a KPI dashboard for a client presentation.",
    "Suggest three quick wins to boost utilisation above 88 %."
]
