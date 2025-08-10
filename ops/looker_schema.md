# ───────────────────────────────────────────────────────────────────────────────
# ops/looker_schema.md
# ───────────────────────────────────────────────────────────────────────────────

# Looker Studio Schema — Arbitrage Dashboard v001

> คู่มือเซ็ตอัป Looker Studio สำหรับ Google Sheet `live_metrics` ของโปรเจกต์นี้

## 1) Data Source Mapping
เลือก **Google Sheets** → ชี้ไปที่ไฟล์เดียวกับที่ระบุใน `config.yaml.sheet.spreadsheet_id` และแท็บ `live_metrics` (หรือชื่อที่ใช้จริง)

### Field Types (ตั้งค่าประเภทข้อมูล)
| Field | Type | Description |
|---|---|---|
| `timestamp_utc` | Date & Time (UTC) | เวลาบันทึกสแนปช็อต |
| `exchange` | Text | ชื่อ exchange (deribit) |
| `base` | Text | ฐานสกุล (BTC) |
| `quote` | Text | สกุลอ้างอิง (USD) |
| `instrument_type` | Text | ประเภท (future/perp/spot-proxy) |
| `instrument` | Text | ชื่อสัญญา (เช่น BTC-29NOV24) |
| `expiry_ts` | Number (Integer) | หมดอายุ (epoch ms) |
| `days_to_expiry` | Number | จำนวนวันถึงหมดอายุ |
| `spot_price` | Number | ราคาอ้างอิง spot/index |
| `perp_price` | Number | ราคา perp ล่าสุด/mark |
| `fut_price` | Number | ราคา future ล่าสุด/mark |
| `spread` | Number | fut − spot |
| `apy_annual` | Number | APY แบบทศนิยม (0.12 = 12%) |
| `z_hist` | Number | Historical z-score (ต่อ expiry) |
| `z_cross` | Number | Cross-sectional z-score (snapshot) |
| `z_term` | Number | Term-curve deviation z |
| `funding_est_hourly` | Number | ค่าประมาณ funding ต่อชั่วโมง |
| `fee_bp_est` | Number | ค่าธรรมเนียมโดยประมาณ (bp) |
| `apy_net` | Number | APY หลังหักต้นทุนโดยคร่าว |
| `liq_depth_bp` | Number | สภาพคล่องเทียบเป็น bps (ถ้ามี) |
| `signal_flag` | Boolean | เป็นสัญญาณเข้าเทรดหรือไม่ |
| `signal_reason` | Text | z ที่ทำให้ติดสัญญาณ |
| `side_hint` | Text | คำแนะนำฝั่ง Long/Short |
| `run_id` | Text | ไอดีการรันครั้งนั้น |

> เคล็ดลับ: เปิด **Field Editing in Reports** เพื่อปรับสูตรในรายงานได้สะดวก

## 2) Recommended Calculated Fields (สร้างใน Looker Studio)
- **`APY %`**: `apy_annual * 100`
- **`Abs Spread`**: `ABS(spread)`
- **`DTE Bin`** (ตัวอย่าง):
  ```
  CASE
    WHEN days_to_expiry <= 7 THEN '0-7d'
    WHEN days_to_expiry <= 14 THEN '8-14d'
    WHEN days_to_expiry <= 30 THEN '15-30d'
    WHEN days_to_expiry <= 60 THEN '31-60d'
    WHEN days_to_expiry <= 90 THEN '61-90d'
    ELSE '90d+'
  END
  ```
- **`Signal Label`**:
  ```
  CASE WHEN signal_flag THEN 'Signal' ELSE 'Normal' END
  ```
- **`Expiry (Date)`**: แปลง `expiry_ts` จาก epoch ms → date (ใช้ฟังก์ชัน **DATETIME_MILLIS** ถ้ามี หรือเตรียมคอลัมน์นี้จากฝั่ง ETL ก็ได้)

## 3) Suggested Charts
1. **Scatter: Spread vs DTE (Latest Snapshot)**
   - Data control: กรองเวลาที่ `timestamp_utc` = ค่าสูงสุด (ใช้ report level filter หรือสร้าง **Latest Flag** field)
   - X: `days_to_expiry` (Number), Y: `spread`
   - Bubble label/tooltip: `instrument`, `apy_annual`, `z_cross`, `z_hist`, `z_term`
   - Color by: `Signal Label` หรือ `z_cross` (Continuous)

2. **Line: APY over Time**
   - Dimension: `timestamp_utc`
   - Breakdown: `instrument` (เลือกบางตัวด้วย filter control)
   - Metric: `apy_annual` (Format → Percent or create `APY %`)
   - Filter: `instrument_type = future`

3. **Heatmap: Cross-sectional Z (time × instrument)**
   - Rows: `instrument`
   - Columns: `timestamp_utc` (time grain: hour or minute)
   - Color: `z_cross`
   - Optional filter: ช่วงเวลาย้อนหลัง N ชั่วโมง/วัน

4. **Scorecards (KPIs)**
   - จำนวน rows ในหน้าต่างเวลา (เช่น 72 ชม.)
   - จำนวนสัญญา (distinct `instrument`)
   - เวลาสแนปช็อตล่าสุด: ใช้ **MAX(timestamp_utc)**
   - Count สัญญาณ: SUM(CASE WHEN signal_flag THEN 1 ELSE 0 END)

## 4) Filters & Controls
- Time range control: ตั้ง default เป็น **Last 7 days** หรือ **Custom (72 hours)**
- Dropdowns:
  - `instrument`
  - `DTE Bin`
  - `Signal Label`
  - `exchange`

## 5) Data Freshness
- เลือก **Auto Refresh** ทุก 15 นาที (หรือเท่ากับ cron จริง 60 นาที)
- ถ้าแผ่นงานใหญ่ขึ้น ให้พิจารณา query limit หรือแยก Data Source เป็น **live (ล่าสุด)** กับ **archive (Parquet ผ่าน BigQuery ในอนาคต)**

## 6) Styling Tips
- ใช้สีต่อเนื่องสำหรับ `z_cross` (เช่น diverging palette) เพื่อเน้นค่าบวก/ลบ
- ฟอนต์อ่านง่าย, แกนเวลาเป็น UTC ให้ชัด
- ใส่คำอธิบายสั้น ๆ ใต้แต่ละชาร์ตว่าเกณฑ์ z/apy คืออะไร

## 7) QA Checklist
- Null/NaN ถูกแปลงเป็น 0 หรือซ่อนไว้อย่างเหมาะสม
- ค่า `z_*` มีสเกลถูกต้อง (คำนวณฝั่ง ETL แล้ว)
- ฟิลเตอร์ `instrument_type` ไม่ตัดทอนข้อมูลที่ต้องใช้
- ชื่อเขตข้อมูล (field names) ตรงกับคอลัมน์ใน Google Sheet จริง ๆ
