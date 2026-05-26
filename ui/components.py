"""
Reusable UI components for Streamlit.
"""
from __future__ import annotations

import html

import streamlit as st


AGENT_ACCENTS = {
    "planner": "#7c3aed",
    "researcher": "#0f9f8f",
    "coder": "#2f80ed",
    "critic": "#f97361",
    "debater": "#f6a623",
}


def _normalize(value: object) -> str:
    return str(value or "").strip().lower()


def _agent_accent(value: object) -> str:
    normalized = _normalize(value)
    for name, color in AGENT_ACCENTS.items():
        if name in normalized:
            return color
    return "#6d5dfc"


def _status_class(status: object) -> str:
    normalized = _normalize(status)
    if normalized in {"running", "done", "error", "cancelled", "pending"}:
        return normalized
    return "default"


def _truncate(value: object, limit: int) -> str:
    text = str(value or "").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)].rstrip()}..."


def agent_card(name, role, status, tokens, cost) -> None:
    safe_name = html.escape(str(name))
    safe_role = html.escape(str(role))
    safe_status = html.escape(str(status or "unknown").upper())
    status_class = _status_class(status)
    accent = _agent_accent(name)

    st.markdown(
        f"""
        <div class="agent-card" style="--agent-accent: {accent};">
            <div class="agent-card__header">
                <div>
                    <h4>{safe_name}</h4>
                    <p>{safe_role}</p>
                </div>
                <span class="agent-status-badge status-{status_class}">
                    {safe_status}
                </span>
            </div>
            <div class="agent-card__footer">
                <span>{int(tokens):,} tokens</span>
                <span>${float(cost):.3f}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def task_event_card(task: dict) -> str:
    status = str(task.get("status", "?"))
    kind = str(task.get("kind", "?"))
    input_snippet = _truncate(task.get("input", ""), 120)
    status_class = _status_class(status)
    accent = _agent_accent(kind)

    return f"""
    <div class="task-event-card" style="--agent-accent: {accent};">
        <div class="task-event-card__top">
            <span class="task-status-badge status-{status_class}">
                {html.escape(status.upper())}
            </span>
            <code>{html.escape(kind)}</code>
        </div>
        <p>{html.escape(input_snippet) if input_snippet else "No input payload"}</p>
    </div>
    """
