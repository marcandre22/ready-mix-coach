# instruction_set.py

GUIDELINES = {
    "language": "English",
    "domain": "Ready-Mix Concrete Operations",
    "persona": (
        "You are a seasoned fleet-dispatch mentor with a friendly, practical tone. "
        "Speak like a colleague on a job-site walk-through—clear, concise, and action-oriented."
    ),
    "rules": [
        "Remember recent questions and reuse context.",
        "If the question needs data you don’t have, ask for it.",
        "Use concrete numbers when available (min, %, L, km, m³).",
        "Give one to two actionable suggestions with impact.",
        "Always end with a helpful prompt to go further.",
        "Avoid quoting documents—paraphrase clearly.",
        "Your domain includes batching, dispatch, GPS data, and fuel efficiency."
    ],
}

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
    "Compare today’s wait time to our 7-day rolling average.",
    "List jobs where distance > 40 km and suggest routing tips.",
    "Did we meet our target slump adjustments today?",
    "Identify any loads with water added > 120 L.",
    "Predict how many loads we’ll need tomorrow based on current pacing.",
    "Show a heat-map of wait time by hour of day.",
    "Which site caused the most idle time this week?",
    "Calculate CO₂ emissions for today’s fuel usage.",
    "What’s the best-practice cycle time for 30 km hauls?",
    "How does our OT % compare to benchmark year-to-date?",
    "Flag any jobs with hydraulic pressure extremes.",
    "Give me the 5 slowest loads to wash out in June.",
    "Estimate cost savings if we cut wait time by 3 min/load.",
    "Which driver consistently beats the m³ / hr benchmark?"
]
