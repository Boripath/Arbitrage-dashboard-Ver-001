# ───────────────────────────────────────────────────────────────────────────────
# streamlit_app/app.py
# ───────────────────────────────────────────────────────────────────────────────
import os
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta, timezone
import plotly.express as px
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from gspread_dataframe import get_as_dataframe

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

@st.cache_data(ttl=300)
def load_sheet(spreadsheet_id: str, worksheet_name: str, sa_json_path: str = None) -> pd.DataFrame:
    """Load Google Sheet into DataFrame. Supports Streamlit Cloud secrets or env path."""
    sa_json = st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON") if "GOOGLE_SERVICE_ACCOUNT_JSON" in st.secrets else None
    if sa_json and not sa_json_path:
        import json, tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        with open(tmp.name, 'w') as f:
            json.dump(sa_json, f)
        sa_json_path = tmp.name
    if not sa_json_path:
        sa_json_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    creds = ServiceAccountCredentials.from_json_keyfile_name(sa_json_path, SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()
    df = get_as_dataframe(ws, evaluate_formulas=True, header=0).dropna(how='all')
    return df


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], errors='coerce', utc=True)
    num_cols = ['days_to_expiry','spot_price','perp_price','fut_price','spread','apy_annual','z_hist','z_cross','z_term','apy_net']
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna(subset=['timestamp_utc','instrument'])
    return df


st.set_page_config(page_title="Arbitrage Dashboard — ver 001", layout="wide")
st.title("Arbitrage Dashboard — ver 001")
st.caption("Data source: Google Sheet (live); Interval: 60 minutes")

# Sidebar
with st.sidebar:
    st.header("Data Source")
    sheet_id = st.text_input("Google Sheet ID", os.getenv('GOOGLE_SHEET_ID', ''))
    ws_name = st.text_input("Worksheet", os.getenv('GOOGLE_SHEET_WORKSHEET', 'live_metrics'))
    st.divider()
    st.header("Filters")
    hours = st.slider("Lookback (hours)", 6, 336, 72)
    base = st.text_input("Base", os.getenv('BASE_ASSET','BTC'))
    st.caption("Tip: Put Service Account JSON in st.secrets as GOOGLE_SERVICE_ACCOUNT_JSON (Streamlit Cloud)")

if not sheet_id:
    st.warning("Please provide Google Sheet ID in the sidebar.")
    st.stop()

raw = load_sheet(sheet_id, ws_name)
if raw.empty:
    st.info("No data loaded yet.")
    st.stop()

df = coerce_types(raw)

# Time window
now = datetime.now(timezone.utc)
start_ts = now - timedelta(hours=hours)
df = df[df['timestamp_utc'] >= start_ts]

# Summary
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Rows", len(df))
with c2: st.metric("Unique Expiries", df['instrument'].nunique())
with c3: st.metric("Latest Snapshot", df['timestamp_utc'].max().strftime('%Y-%m-%d %H:%M UTC'))
with c4: st.metric("Signals (net)", int(df.get('signal_flag', pd.Series(dtype=bool)).fillna(False).sum()))

# 1) Spread vs DTE (latest snapshot)
st.subheader("1) Scatter: Spread vs Days-to-Expiry (latest snapshot)")
latest_ts = df['timestamp_utc'].max()
latest_df = df[df['timestamp_utc'] == latest_ts]
if latest_df.empty:
    st.write("No latest snapshot.")
else:
    fig1 = px.scatter(latest_df, x='days_to_expiry', y='spread', hover_data=['instrument','apy_annual','z_cross','z_hist','z_term'])
    fig1.update_layout(xaxis_title='Days to Expiry', yaxis_title='Spread')
    st.plotly_chart(fig1, use_container_width=True)

# 2) APY Timeline
st.subheader("2) APY Timeline (select instruments)")
choices = sorted(df['instrument'].unique().tolist())
sel = st.multiselect("Instruments", choices[:5], max_selections=8)
plot_df = df[df['instrument'].isin(sel)] if sel else df
if plot_df.empty:
    st.write("Select instruments to view APY timeline.")
else:
    fig2 = px.line(plot_df, x='timestamp_utc', y='apy_annual', color='instrument', hover_data=['days_to_expiry'])
    fig2.update_layout(yaxis_title='APY (annualized)', xaxis_title='Time (UTC)')
    st.plotly_chart(fig2, use_container_width=True)

# 3) Heatmap of z_cross
st.subheader("3) Heatmap: Cross-sectional Z (time × instrument)")
piv = df.pivot_table(index='timestamp_utc', columns='instrument', values='z_cross', aggfunc='mean')
if piv.empty:
    st.write("Insufficient data for heatmap.")
else:
    fig3 = px.imshow(piv.T, aspect='auto', origin='lower', labels=dict(x='Time (UTC)', y='Instrument', color='z_cross'))
    st.plotly_chart(fig3, use_container_width=True)

st.caption("v001 • Charts: Spread–DTE, APY timeline, z_cross heatmap • Data refresh via cache (5 min)")
