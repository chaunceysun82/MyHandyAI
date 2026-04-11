"""
Utility functions for content generation.
Extracted from legacy_modules/chatbot/agents.py to avoid dependencies on deprecated code.
"""
import os


def load_prompt(filename):
    """
    Load prompt from file, removing comment lines starting with #.
    Looks for prompts in the prompts/ directory relative to the project root.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level from content_generation/ to Backend/, then to prompts/
    path = os.path.join(script_dir, "..", "prompts", filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        return "".join(line for line in lines if not line.strip().startswith("#"))
    except FileNotFoundError:
        print(f"❌ Could not find prompt file: {path}")
        return f"Error: Could not load {filename}"
    except Exception as e:
        print(f"❌ Error loading prompt file {filename}: {e}")
        return f"Error: Could not load {filename}"


def minutes_to_human(minutes: int) -> str:
    """
    Convert integer minutes to 'X hr Y min' or 'Y min'.
    """
    if minutes is None:
        return "unknown"
    try:
        m = int(minutes)
    except Exception:
        return str(minutes)
    if m <= 0:
        return "0 min"
    hrs, mins = divmod(m, 60)
    if hrs and mins:
        return f"{hrs} hr {mins} min"
    if hrs:
        return f"{hrs} hr"
    return f"{mins} min"
