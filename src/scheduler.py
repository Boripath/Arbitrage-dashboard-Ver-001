# ───────────────────────────────────────────────────────────────────────────────
# src/scheduler.py
# ───────────────────────────────────────────────────────────────────────────────
import os, uuid, yaml
import pandas as pd
from dotenv import load_dotenv
from .utils_logging import setup_logger
from .utils_google import GoogleClients
from .fetch_deribit import fetch_spot_perp_future_prices
from .compute_metrics import compute_all_metrics
from .write_google_sheet import append_metrics_to_sheet
from .alerts import send_alerts


def load_config(path: str = 'config.yaml'):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def main():
    log = setup_logger()
    load_dotenv()
    cfg = load_config()

    sa = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    gc = GoogleClients(sa)

    sheet_cfg = cfg['sheet']
    notif_cfg = cfg['notifications']
    app_cfg = cfg['app']

    # 1) Fetch current snapshot from Deribit
    cur = fetch_spot_perp_future_prices(base=app_cfg['base_asset'], quote=app_cfg['quote_asset'])
    run_id = str(uuid.uuid4())[:8]
    cur['run_id'] = run_id

    # 2) Pull history tail from Google Sheet for rolling stats
    hist = gc.read_sheet_tail(sheet_cfg['spreadsheet_id'], sheet_cfg['worksheet_name'], n_rows=sheet_cfg['history_pull_rows'])

    # 3) Compute metrics
    term_bins = cfg['term_curve_bins']
    df = compute_all_metrics(cur, hist, term_bins,
                             lookback_days_for_hist_z=app_cfg['lookback_days_for_hist_z'],
                             min_history_rows_per_expiry=app_cfg['min_history_rows_per_expiry'])

    # 4) Decide signals (apply thresholds & basic side hint)
    th = cfg['thresholds']
    def decide(row):
        cond = (
            (abs(row.get('z_hist',0)) >= th['z_hist_enter']) or
            (abs(row.get('z_cross',0)) >= th['z_cross_enter']) or
            (abs(row.get('z_term',0)) >= th['z_term_enter'])
        ) and (row.get('apy_net',0) >= th['apy_net_min'])
        # side hint: if future rich vs spot → short future / long perp
        side = 'Short Future (rich) / Long Perp (cheap)' if row['spread']>0 else 'Long Future (cheap) / Short Perp (rich)'
        reason = []
        if abs(row.get('z_hist',0)) >= th['z_hist_enter']: reason.append('z_hist')
        if abs(row.get('z_cross',0)) >= th['z_cross_enter']: reason.append('z_cross')
        if abs(row.get('z_term',0)) >= th['z_term_enter']: reason.append('z_term')
        return pd.Series({
            'signal_flag': bool(cond),
            'signal_reason': ','.join(reason),
            'side_hint': side,
            'liq_depth_bp': None,  # future: compute from orderbook
        })

    sig = df.apply(decide, axis=1)
    df = pd.concat([df, sig], axis=1)

    # 5) Write to Google Sheet
    append_metrics_to_sheet(gc, sheet_cfg['spreadsheet_id'], sheet_cfg['worksheet_name'], df)
    log.info(f"Appended {len(df)} rows to sheet. run_id={run_id}")

    # 6) Send alerts for rows with signal
    enabled = notif_cfg.get('enabled_channels', [])
    for _, row in df[df['signal_flag']==True].iterrows():
        send_alerts(row, enabled, notif_cfg)
        log.info(f"Alert sent for {row['instrument']}")

if __name__ == "__main__":
    main()
