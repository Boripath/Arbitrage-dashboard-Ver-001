# ───────────────────────────────────────────────────────────────────────────────
# src/utils_zscore.py
# ───────────────────────────────────────────────────────────────────────────────
import numpy as np
import pandas as pd

def rolling_z_by_group(df: pd.DataFrame, value_col: str, group_col: str, time_col: str,
                       lookback_rows: int = 200, min_rows: int = 30) -> pd.Series:
    # compute z within each group using last N rows (per group)
    z = []
    for key, g in df.sort_values(time_col).groupby(group_col, dropna=False):
        vals = g[value_col].astype(float)
        if len(vals) < min_rows:
            z.extend([np.nan]*len(vals))
            continue
        roll = vals.rolling(window=min(len(vals), lookback_rows), min_periods=min_rows)
        mean = roll.mean(); std = roll.std(ddof=0)
        z.extend(((vals - mean) / std).tolist())
    return pd.Series(z, index=df.sort_values(time_col).index)


def cross_sectional_z(snapshot_df: pd.DataFrame, value_col: str, by_col: str) -> pd.Series:
    # Z across instruments in the same timestamp
    if snapshot_df.empty:
        return pd.Series(dtype=float)
    grp = snapshot_df.groupby(by_col)[value_col]
    mean = grp.transform('mean')
    std = grp.transform('std').replace(0, np.nan)
    return (snapshot_df[value_col] - mean) / std
