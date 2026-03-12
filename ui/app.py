import streamlit as st
from core.agent_loop import run_agent

st.title("Autonomous AI Researcher")

task = st.text_input("Research Question")

if st.button("Run Research"):

    result = run_agent(task)

    st.write(result)