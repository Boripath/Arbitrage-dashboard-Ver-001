# ───────────────────────────────────────────────────────────────────────────────
# streamlit_app/app.py  (stub; connect to Sheet later)
# ───────────────────────────────────────────────────────────────────────────────
import os
import pandas as pd
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Arb Dashboard", layout="wide")

st.title("Arbitrage Dashboard — ver 001")
st.caption("Data source: Google Sheet (live); Interval: 60 minutes")

st.info("🔧 Connect to Google Sheet and Parquet archive in the next iteration.")
