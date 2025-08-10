# Arbitrage-dashboard-Ver-001

#arbitrage-dashboard/
#├─ requirements.txt
#├─ config.yaml                       # ตั้งค่า exchange, intervals, thresholds, keys, sheet ids ฯลฯ
#├─ secrets/.env                      # token/keys (อย่า commit)
#├─ src/
#│  ├─ fetch_deribit.py               # ดึง Spot/Perp/Futures + orderbook depth
#│  ├─ compute_metrics.py             # spread, APY, z_hist, z_cross, z_term
#│  ├─ write_google_sheet.py          # append/overwrite Google Sheet (gspread)
#│  ├─ archive_parquet.py             # รวมวัน → เขียน Parquet ไป GDrive (pydrive2)
#│  ├─ alerts.py                      # LINE/Discord/Telegram notifier + debounce
#│  ├─ scheduler.py                   # เรียงลำดับ: fetch→compute→write→alert (ใช้ใน cron)
#│  ├─ utils_google.py                # auth Google (Service Account) + helpers
#│  ├─ utils_termcurve.py             # LOWESS/spline/bin model สำหรับ term structure
#│  ├─ utils_zscore.py                # ฟังก์ชัน zscore rolling + cross-section
#│  └─ utils_logging.py               # structured logging + error handling
#├─ streamlit_app/
#│  └─ app.py                         # อ่านจาก Sheet/Parquet แสดงกราฟ+ตาราง+ฟิลเตอร์
#└─ ops/
#   ├─ crontab.example                # ตัวอย่าง cron schedule
#   └─ looker_schema.md               # คำแนะนำตั้ง Looker fields/visuals
