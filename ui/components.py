"""
Reusable UI components for Streamlit.
"""
import streamlit as st
import html

def agent_card(name: str, role: str, status: str, tokens: int, cost: float):
    safe_name = html.escape(str(name))
    safe_role = html.escape(str(role))
    safe_status = html.escape(str(status))
    
    st.markdown(f"""
    <div style="border: 1px solid #ddd; padding: 16px 18px; border-radius: 8px; margin: 0 0 14px 0; line-height: 1.5;">
        <h4 style="margin: 0 0 8px 0;">{safe_name} <small style="color: gray;">({safe_role})</small></h4>
        <p style="margin: 0 0 6px 0;"><b>Status:</b> {safe_status}</p>
        <p style="margin: 0; font-size: 0.8em; color: gray;">Tokens: {tokens} | Cost: ${cost:.3f}</p>
    </div>
    """, unsafe_allow_html=True)
