from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {"business", "hours", "services", "booking", "cancellation", "escalate_if"}


def load_sop(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        sop = json.load(file)

    missing = REQUIRED_FIELDS - set(sop)
    if missing:
        missing_fields = ", ".join(sorted(missing))
        raise ValueError(f"SOP file is missing required fields: {missing_fields}")

    if not isinstance(sop["services"], list) or not sop["services"]:
        raise ValueError("SOP field 'services' must be a non-empty list.")

    return sop


def sop_to_context(sop: dict[str, Any]) -> str:
    services = "\n".join(
        f"- {service['name']}: {service['price']}" for service in sop["services"]
    )
    escalation_rules = "\n".join(f"- {rule}" for rule in sop["escalate_if"])
    return (
        f"Business: {sop['business']}\n"
        f"Hours: {sop['hours']}\n"
        f"Services:\n{services}\n"
        f"Booking: {sop['booking']}\n"
        f"Cancellation: {sop['cancellation']}\n"
        f"Escalate if:\n{escalation_rules}"
    )
