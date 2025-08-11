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
        "Use concrete numbers when available (min, %, L, km, m³).",
        "Give one to two actionable suggestions with impact and quantify time/$ when possible.",
        "End with a short prompt to go further.",
        "Paraphrase reference notes—do not quote docs verbatim.",
        "Your domain includes batching, dispatch, GPS/telematics, QC, and fuel efficiency."
    ],
}

# 25 prompts that are 100% computable with our dataset
SUGGESTED_PROMPTS = [
    "What was our total delivered volume today vs. yesterday?",
    "Which driver added the most water this week?",
    "Show the top three jobs with the longest wait times in the last 48 hours.",
    "How does our utilization compare to the 85 % benchmark for the past 7 days?",
    "Which stage is causing the biggest delay this week?",
    "Estimate the fuel cost for today’s deliveries at $1.80 /L.",
    "Who is our most efficient driver by m³ / hr today?",
    "Highlight any outliers in drum RPM this week.",
    "Give me a breakdown of average cycle time per plant this week.",
    "Which projects exceeded the target m³ / load (target 9.5)?",
    "Compare today’s wait time to our 7-day rolling average.",
    "List jobs where distance > 40 km and suggest routing tips.",
    "Identify any loads with water added > 120 L this week.",
    "Predict how many loads we’ll do tomorrow based on the last 7 days.",
    "Which hours today had the worst wait times?",
    "Which site caused the most total waiting time this week?",
    "Calculate CO₂ emissions for today’s fuel usage.",
    "What’s the empirical best-practice cycle time for ~30 km hauls from our data?",
    "Flag any jobs with hydraulic pressure extremes this week.",
    "Give me the 5 slowest washout times this week.",
    "Show me the top 3 cost-saving opportunities this week.",
    "Which driver consistently beats the m³ / hr benchmark (≥ 3.5) this week?",
    "Rank plants by average cycle time this week.",
    "Identify days this week when fuel L / km exceeded 0.55.",
    "Suggest three quick wins to boost utilization above 88 %.",
]
