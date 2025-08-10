# ───────────────────────────────────────────────────────────────────────────────
# src/alerts.py
# ───────────────────────────────────────────────────────────────────────────────
import os, time, json, requests
import pandas as pd


def _line_notify(token: str, message: str):
    if not token:
        return
    url = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {token}'}
    requests.post(url, headers=headers, data={'message': message}, timeout=10)


def _discord_hook(url: str, content: str):
    if not url:
        return
    requests.post(url, json={'content': content}, timeout=10)


def _telegram_bot(token: str, chat_id: str, text: str):
    if not token or not chat_id:
        return
    requests.get(f"https://api.telegram.org/bot{token}/sendMessage", params={'chat_id': chat_id, 'text': text}, timeout=10)


def format_signal_row(row: pd.Series) -> str:
    return (
        f"[ARBI] {row['timestamp_utc']} | {row['exchange']} | {row['instrument']} | DTE={int(row['days_to_expiry'])}\n"
        f"APY={row['apy_annual']*100:.2f}% | zH={row.get('z_hist',float('nan')):.2f} "
        f"zX={row.get('z_cross',float('nan')):.2f} zT={row.get('z_term',float('nan')):.2f} | apy_net={row['apy_net']*100:.2f}%\n"
        f"Side: {row.get('side_hint','n/a')} | Reason: {row.get('signal_reason','') }"
    )


def send_alerts(row: pd.Series, channels: list, conf: dict):
    msg = format_signal_row(row)
    if 'line' in channels:
        _line_notify(os.getenv('LINE_NOTIFY_TOKEN', conf.get('line_notify_token','')), msg)
    if 'discord' in channels:
        _discord_hook(os.getenv('DISCORD_WEBHOOK_URL', conf.get('discord_webhook_url','')), msg)
    if 'telegram' in channels:
        _telegram_bot(os.getenv('TELEGRAM_BOT_TOKEN', conf.get('telegram_bot_token','')),
                      os.getenv('TELEGRAM_CHAT_ID', conf.get('telegram_chat_id','')), msg)
