# prompt_utils.py – helper to build a consistent system prompt
def build_system_prompt(GUIDELINES: dict, COACH_STYLE: dict) -> str:
    persona = GUIDELINES.get("persona", "")
    rules = "\n".join(f"- {r}" for r in GUIDELINES.get("rules", []))
    voice = COACH_STYLE.get("voice", "direct, supportive, insightful")
    closing = COACH_STYLE.get("closing", "Always end with a question or prompt to help the user go further.")
    return (
        f"{persona}\n\n"
        f"Voice: {voice}.\n\n"
        f"Ground rules:\n{rules}\n\n"
        f"Closing rule: {closing}\n"
        f"Be precise, prefer concrete numbers from tools."
    )
