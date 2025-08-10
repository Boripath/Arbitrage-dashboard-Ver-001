# ───────────────────────────────────────────────────────────────────────────────
# src/utils_termcurve.py
# ───────────────────────────────────────────────────────────────────────────────
import numpy as np
import pandas as pd
from statsmodels.nonparametric.smoothers_lowess import lowess

def fit_term_curve_lowess(dte: np.ndarray, spread: np.ndarray, frac: float = 0.6):
    # LOWESS expects x sorted
    order = np.argsort(dte)
    x = dte[order]; y = spread[order]
    if len(x) < 5:
        return None
    try:
        sm = lowess(y, x, frac=frac, return_sorted=True)
        xs, ys = sm[:,0], sm[:,1]
        def predict(d):
            return np.interp(d, xs, ys)
        return predict
    except Exception:
        return None

def fit_term_curve_bins(dte: np.ndarray, spread: np.ndarray, bins):
    df = pd.DataFrame({"dte": dte, "spread": spread}).dropna()
    if df.empty:
        return None
    df['bin'] = pd.cut(df['dte'], bins=bins, include_lowest=True)
    means = df.groupby('bin')['spread'].mean()
    edges = [b.left for b in means.index.categories] + [means.index.categories[-1].right]
    vals = means.values
    def predict(d):
        # piecewise constant by bin mid; interpolate edges to be safe
        return np.interp(d, np.array(edges, dtype=float), np.r_[vals[0], vals])
    return predict
