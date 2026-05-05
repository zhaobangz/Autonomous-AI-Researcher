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
    <div style="border: 1px solid #ddd; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
        <h4>{safe_name} <small style="color: gray;">({safe_role})</small></h4>
        <p><b>Status:</b> {safe_status}</p>
        <p style="font-size: 0.8em; color: gray;">Tokens: {tokens} | Cost: ${cost:.3f}</p>
    </div>
    """, unsafe_allow_html=True)
