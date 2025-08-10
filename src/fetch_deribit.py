# ───────────────────────────────────────────────────────────────────────────────
# src/fetch_deribit.py
# ───────────────────────────────────────────────────────────────────────────────
import requests, time
import pandas as pd
from datetime import datetime, timezone

DERIBIT_API = "https://www.deribit.com/api/v2"

def _get(url, params=None):
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def fetch_spot_perp_future_prices(base="BTC", quote="USD") -> pd.DataFrame:
    # Deribit doesn't have classic spot; use index price for spot proxy
    # 1) Index price
    idx = _get(f"{DERIBIT_API}/public/get_index_price", {"index_name": f"{base}-{quote}"})
    spot = idx['result']['index_price']

    # 2) Perp price via ticker
    perp_instr = f"{base}-PERPETUAL"
    perp = _get(f"{DERIBIT_API}/public/ticker", {"instrument_name": perp_instr})['result']
    perp_price = perp['last_price'] or perp['mark_price']

    # 3) Futures instruments and last price
    insts = _get(f"{DERIBIT_API}/public/get_instruments", {"currency": base, "kind": "future", "expired": False})['result']
    rows = []
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    ts = now.isoformat()
    for it in insts:
        name = it['instrument_name']
        exp_ms = it['expiration_timestamp']
        dte = max(1, int((datetime.fromtimestamp(exp_ms/1000, tz=timezone.utc) - now).days))
        t = _get(f"{DERIBIT_API}/public/ticker", {"instrument_name": name})['result']
        fut_price = t['last_price'] or t['mark_price']
        rows.append({
            'timestamp_utc': ts,
            'exchange': 'deribit',
            'base': base,
            'quote': quote,
            'instrument_type': 'future',
            'instrument': name,
            'expiry_ts': exp_ms,
            'days_to_expiry': dte,
            'spot_price': spot,
            'perp_price': perp_price,
            'fut_price': fut_price,
        })
    return pd.DataFrame(rows)
