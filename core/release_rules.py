from __future__ import annotations

from typing import Any, Dict, Tuple


def classify_release_status(context: Dict[str, Any]) -> Tuple[str, str, str]:
    execution_error = str(context.get("execution_error") or "").strip()
    qa_detail = context.get("qa_detail") or {}
    structural_bugs = qa_detail.get("structural_bugs") or []
    functional_bugs = qa_detail.get("functional_bugs") or []
    prd_gaps = qa_detail.get("prd_gaps") or []
    regression_bugs = qa_detail.get("regression_bugs") or []
    ui_gaps = qa_detail.get("ui_gaps") or []

    if execution_error or structural_bugs or functional_bugs or prd_gaps or regression_bugs:
        return (
            "RETRY",
            "BLOCKER",
            "Build failed, ownership/integration failed, or story acceptance criteria are incomplete.",
        )
    if ui_gaps:
        return (
            "DONE",
            "MINOR",
            "Build and current story requirements passed, with only minor UI gaps remaining.",
        )
    return (
        "DONE",
        "NONE",
        "Build passed and no important QA gaps remain for the current story.",
    )
