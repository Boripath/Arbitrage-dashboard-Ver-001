# ───────────────────────────────────────────────────────────────────────────────
# src/write_google_sheet.py
# ───────────────────────────────────────────────────────────────────────────────
import pandas as pd
from .utils_google import GoogleClients

def append_metrics_to_sheet(gc: GoogleClients, spreadsheet_id: str, worksheet_name: str, df: pd.DataFrame):
    # Ensure column order
    cols = [
        'timestamp_utc','exchange','base','quote','instrument_type','instrument',
        'expiry_ts','days_to_expiry','spot_price','perp_price','fut_price',
        'spread','apy_annual','z_hist','z_cross','z_term',
        'funding_est_hourly','fee_bp_est','apy_net','liq_depth_bp',
        'signal_flag','signal_reason','side_hint','run_id'
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    out = df[cols].copy()
    gc.append_rows(spreadsheet_id, worksheet_name, out)
