# prompt_utils.py – builds structured system prompt from config
def build_system_prompt(guidelines: dict, style: dict) -> str:
    assert "persona" in guidelines, "Missing 'persona' in GUIDELINES"
    assert "rules" in guidelines and isinstance(guidelines["rules"], list), "Missing or invalid 'rules'"
    assert "voice" in style, "Missing 'voice' in COACH_STYLE"

    parts = [
        f"{guidelines['persona']}",
        f"Speak in a {style['voice']} tone.",
        "",
        "Instructions:",
        *[f"- {rule}" for rule in guidelines["rules"]],
    ]

    if "avoid" in style:
        parts.append("\nAvoid:")
        parts += [f"- {a}" for a in style["avoid"]]

    if "closing" in style:
        parts.append(f"\nClosing Guideline: {style['closing']}")

    return "\n".join(parts)