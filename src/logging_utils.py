from __future__ import annotations

import logging


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


def log_escalation(reason: str | None, trigger: str | None) -> None:
    logging.getLogger("support_workflow").info(
        "Escalation triggered | trigger=%s | reason=%s",
        trigger or "model_or_low_confidence",
        reason or "No reason provided",
    )
