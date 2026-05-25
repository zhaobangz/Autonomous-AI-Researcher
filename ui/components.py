"""
Reusable UI components for Streamlit.
"""
import html

import streamlit as st


def _status_styles(status: str) -> tuple[str, str, str]:
    normalized = str(status or "").lower()
    if normalized == "running":
        return "#0f766e", "#ccfbf1", "#115e59"
    if normalized == "done":
        return "#15803d", "#dcfce7", "#166534"
    if normalized == "error":
        return "#b91c1c", "#fee2e2", "#991b1b"
    return "#617087", "#eef2f7", "#465469"


def _task_status_styles(status: str) -> tuple[str, str]:
    normalized = str(status or "").lower()
    if normalized == "running":
        return "#dbeafe", "#1d4ed8"
    if normalized == "done":
        return "#dcfce7", "#166534"
    if normalized == "error":
        return "#fee2e2", "#991b1b"
    return "#eef2f7", "#465469"


def _truncate(value: object, limit: int) -> str:
    text = str(value or "").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)].rstrip()}…"


def agent_card(name, role, status, tokens, cost):
    safe_name = html.escape(str(name))
    safe_role = html.escape(str(role))
    safe_status = html.escape(str(status or "unknown").upper())
    accent, badge_bg, badge_text = _status_styles(status)

    st.markdown(
        f"""
        <div class="agent-card" style="background: #ffffff; border: 1px solid #d8dee8; border-left: 5px solid {accent}; border-radius: 14px; box-shadow: 0 4px 24px rgba(23,32,51,0.08); margin: 0 0 0.9rem; padding: 1rem;">
            <div class="agent-card__header" style="align-items: flex-start; display: flex; gap: 0.8rem; justify-content: space-between;">
                <div>
                    <h4 style="color: #172033; font-size: 1rem; margin: 0 0 0.2rem;">{safe_name}</h4>
                    <p style="color: #617087; font-size: 0.88rem; margin: 0;">{safe_role}</p>
                </div>
                <span class="agent-status-badge" style="background: {badge_bg}; border-radius: 999px; color: {badge_text}; display: inline-flex; font-size: 0.72rem; font-weight: 850; letter-spacing: 0; line-height: 1; padding: 0.34rem 0.55rem; text-transform: uppercase;">
                    {safe_status}
                </span>
            </div>
            <div class="agent-card__footer" style="border-top: 1px solid #d8dee8; color: #617087; display: flex; flex-wrap: wrap; font-size: 0.82rem; font-weight: 700; gap: 0.75rem; margin-top: 0.9rem; padding-top: 0.75rem;">
                <span>🔢 {int(tokens):,} tokens</span>
                <span>💰 ${float(cost):.3f}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def task_event_card(task: dict) -> str:
    status = str(task.get("status", "?"))
    kind = str(task.get("kind", "?"))
    input_snippet = _truncate(task.get("input", ""), 80)
    badge_bg, badge_text = _task_status_styles(status)

    return f"""
    <div class="task-event-card" style="background: #ffffff; border: 1px solid #d8dee8; border-radius: 14px; box-shadow: 0 4px 24px rgba(23,32,51,0.08); margin: 0 0 0.75rem; padding: 0.95rem 1rem;">
        <div class="task-event-card__top" style="align-items: center; display: flex; gap: 0.65rem; margin-bottom: 0.55rem;">
            <span class="task-status-badge" style="background: {badge_bg}; border-radius: 999px; color: {badge_text}; display: inline-flex; font-size: 0.72rem; font-weight: 850; letter-spacing: 0; line-height: 1; padding: 0.34rem 0.55rem; text-transform: uppercase;">
                {html.escape(status.upper())}
            </span>
            <code style="background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 7px; color: #172033; font-size: 0.84rem; padding: 0.17rem 0.38rem;">{html.escape(kind)}</code>
        </div>
        <p style="color: #617087; font-size: 0.92rem; line-height: 1.45; margin: 0;">{html.escape(input_snippet) if input_snippet else "No input payload"}</p>
    </div>
    """
