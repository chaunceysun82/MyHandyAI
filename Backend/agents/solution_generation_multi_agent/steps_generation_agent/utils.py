"""Utility functions for steps generation agent."""


def minutes_to_human(minutes: int) -> str:
    """Convert integer minutes to 'X hr Y min' or 'Y min'."""
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


def assess_complexity(total_time: int, total_steps: int) -> str:
    """Assess the complexity level based on time and steps."""
    if total_time <= 60 and total_steps <= 3:
        return "Easy"
    elif total_time <= 180 and total_steps <= 5:
        return "Moderate"
    elif total_time <= 360 and total_steps <= 8:
        return "Challenging"
    else:
        return "Complex"
