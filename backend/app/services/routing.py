import json
import os

from app.api.schemas import Impact, Priority, Urgency

DEFAULT_TEAMS = {
    "Network": "Network Support",
    "Hardware": "Hardware Support",
    "Software": "Application Support",
    "Account Access": "Identity & Access Support",
    "Other": "General Support",
    "Unclassified": "General Support",
}
overrides = json.loads(os.getenv("TEAM_ROUTING_JSON", "{}"))
if not isinstance(overrides, dict) or any(
    category not in DEFAULT_TEAMS
    or not isinstance(team, str)
    or not team.strip()
    or len(team) > 120
    for category, team in overrides.items()
):
    raise ValueError("TEAM_ROUTING_JSON must map known categories to team names of 1–120 characters.")
TEAMS = DEFAULT_TEAMS | overrides


def initial_priority(impact: Impact | None, urgency: Urgency | None) -> Priority:
    if impact == "Organization" and urgency == "Blocked":
        return "Critical"
    if impact == "Organization" or urgency == "Blocked":
        return "High"
    if impact == "Individual" and urgency == "Routine":
        return "Low"
    return "Medium"
