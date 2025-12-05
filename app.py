import streamlit as st
import sys
import os

# Add current directory to path so we can import modules
sys.path.append(os.path.dirname(__file__))

import portfolio_manager.streamlit_app as pm

# Page Config
st.set_page_config(page_title="Antigravity Power Tracker", layout="wide")

# Redirect directly to Portfolio Manager (which now includes the Research Framework)
if __name__ == "__main__":
    pm.run()



