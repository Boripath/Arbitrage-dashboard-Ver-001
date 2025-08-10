import os, yaml
import pandas as pd
from datetime import datetime, timedelta, timezone
from .utils_logging import setup_logger
from .utils_google import GoogleClients
from dotenv import load_dotenv

def load_config(path: str = 'config.yaml'):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def main():
    log = setup_logger()
    load_dotenv()
    cfg = load_config()
    sa = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    gc = GoogleClients(sa)

    sheet_cfg = cfg['sheet']
    arch_cfg = cfg['archive']

    # Archive "yesterday" UTC by default (or ARB_ARCHIVE_DATE=YYYY-MM-DD)
    target_str = os.getenv('ARB_ARCHIVE_DATE')
    if target_str:
        target_date = datetime.fromisoformat(target_str).date()
    else:
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    # Prefer full read for accurate day split; fallback to tail if needed
    try:
        df = gc.read_sheet_all(sheet_cfg['spreadsheet_id'], sheet_cfg['worksheet_name'])
    except Exception:
        df = gc.read_sheet_tail(sheet_cfg['spreadsheet_id'], sheet_cfg['worksheet_name'], n_rows=999999)

    if df.empty:
        log.info("No data in sheet; nothing to archive.")
        return

    # Parse timestamp and filter by date (UTC)
    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], errors='coerce', utc=True)
    df = df.dropna(subset=['timestamp_utc'])
    df['date'] = df['timestamp_utc'].dt.date
    day_df = df[df['date'] == target_date].copy()

    if day_df.empty:
        log.info(f"No rows to archive for {target_date}.")
        return

    # Enforce numeric dtypes for compact parquet
    num_cols = ['expiry_ts','days_to_expiry','spot_price','perp_price','fut_price','spread','apy_annual',
                'z_hist','z_cross','z_term','funding_est_hourly','fee_bp_est','apy_net','liq_depth_bp']
    for c in num_cols:
        if c in day_df.columns:
            day_df[c] = pd.to_numeric(day_df[c], errors='coerce')

    # Write parquet locally
    out_dir = arch_cfg['out_dir']
    ensure_dir(out_dir)
    fname = f"arbitrage_{target_date.isoformat()}.parquet"
    local_path = os.path.join(out_dir, fname)
    day_df.drop(columns=['date'], errors='ignore').to_parquet(local_path, index=False)

    # Upload to Google Drive
    drive_id = gc.upload_to_drive(arch_cfg['drive_folder_id'], local_path, fname)
    log.info(f"Uploaded {fname} to Drive id={drive_id}; rows={len(day_df)}")

if __name__ == "__main__":
    main()
