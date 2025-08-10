# ───────────────────────────────────────────────────────────────────────────────
# src/compute_metrics.py
# ───────────────────────────────────────────────────────────────────────────────
import numpy as np
import pandas as pd
from datetime import datetime
from .utils_zscore import cross_sectional_z
from .utils_termcurve import fit_term_curve_lowess, fit_term_curve_bins


def compute_all_metrics(current_df: pd.DataFrame,
                        history_df: pd.DataFrame,
                        term_bins,
                        lookback_days_for_hist_z: int = 30,
                        min_history_rows_per_expiry: int = 60,
                        fee_bp_est: float = 2.0,
                        funding_est_hourly: float = 0.0) -> pd.DataFrame:
    df = current_df.copy()
    # Basic spread & APY
    df['spread'] = df['fut_price'] - df['spot_price']
    df['apy_annual'] = (df['spread'] / df['spot_price']) * (365.0 / df['days_to_expiry'].clip(lower=1))

    # Cross-sectional Z (snapshot across futures of various DTE)
    df['z_cross'] = (df['apy_annual'] - df['apy_annual'].mean()) / df['apy_annual'].std(ddof=0)

    # Historical Z per expiry: need history (by instrument)
    z_hist = []
    z_term = []
    # Prepare historical set limited by lookback days
    if not history_df.empty:
        hist = history_df.copy()
        # coerce types
        hist['apy_annual'] = pd.to_numeric(hist.get('apy_annual'), errors='coerce')
        hist['spread'] = pd.to_numeric(hist.get('spread'), errors='coerce')
        hist['days_to_expiry'] = pd.to_numeric(hist.get('days_to_expiry'), errors='coerce')
        hist = hist.dropna(subset=['instrument','apy_annual','spread','days_to_expiry'])
        # For each instrument now, compute z_hist using that instrument's last N rows
        for _, row in df.iterrows():
            inst = row['instrument']
            h = hist[hist['instrument'] == inst].tail(1000)
            if len(h) >= min_history_rows_per_expiry and h['apy_annual'].std(ddof=0) > 0:
                z_h = (row['apy_annual'] - h['apy_annual'].mean()) / h['apy_annual'].std(ddof=0)
            else:
                z_h = np.nan
            z_hist.append(z_h)
        # Term-structure deviation: fit curve on history (all futures)
        h2 = hist[['days_to_expiry','spread']].dropna()
        predict = fit_term_curve_lowess(h2['days_to_expiry'].values, h2['spread'].values, frac=0.6)
        if predict is None:
            predict = fit_term_curve_bins(h2['days_to_expiry'].values, h2['spread'].values, bins=term_bins)
        if predict is not None:
            curve_vals = df['days_to_expiry'].apply(lambda d: predict(float(d)))
            dev = df['spread'] - curve_vals
            # Normalize dev using history of dev
            h2['curve'] = predict(h2['days_to_expiry'].values)
            h2['dev'] = h2['spread'] - h2['curve']
            if h2['dev'].std(ddof=0) > 0:
                z_t = (dev - h2['dev'].mean()) / h2['dev'].std(ddof=0)
                z_term = z_t.tolist()
            else:
                z_term = [np.nan]*len(df)
        else:
            z_term = [np.nan]*len(df)
    else:
        z_hist = [np.nan]*len(df)
        z_term = [np.nan]*len(df)

    if len(z_hist) != len(df):
        # fill if not computed above due to branch
        z_hist = z_hist if z_hist else [np.nan]*len(df)
    df['z_hist'] = pd.Series(z_hist, index=df.index)
    df['z_term'] = pd.Series(z_term, index=df.index)

    # Fee & funding estimation (simple placeholder)
    df['funding_est_hourly'] = funding_est_hourly
    df['fee_bp_est'] = fee_bp_est
    fee_frac = df['fee_bp_est'] / 10000.0
    df['apy_net'] = df['apy_annual'] - fee_frac * 365  # rough annualized fee impact

    # Signal logic placeholder; decision refined in scheduler
    return df
