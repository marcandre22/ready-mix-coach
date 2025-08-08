# prompt_utils.py – system prompt builder (keeps style/instructions separate)

def build_system_prompt(guidelines: dict, coach_style: dict) -> str:
    persona = guidelines.get("persona", "")
    rules = guidelines.get("rules", [])
    style_voice = coach_style.get("voice", "")
    style_avoid = ", ".join(coach_style.get("avoid", []))
    closing = coach_style.get("closing", "")

    return (
        f"{persona}\n\n"
        "Rules:\n- " + "\n- ".join(rules) + "\n\n"
        "Tone:\n"
        f"- Voice: {style_voice}\n"
        f"- Avoid: {style_avoid}\n"
        f"- Closing: {closing}\n"
    )
