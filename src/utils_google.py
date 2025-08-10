# ───────────────────────────────────────────────────────────────────────────────
# src/utils_google.py
# ───────────────────────────────────────────────────────────────────────────────
import os, io, json, time
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

class GoogleClients:
    def __init__(self, sa_json_path: str):
        creds = ServiceAccountCredentials.from_json_keyfile_name(sa_json_path, SCOPES)
        self.gc = gspread.authorize(creds)
        # PyDrive2 auth
        gauth = GoogleAuth()
        gauth.credentials = creds
        self.drive = GoogleDrive(gauth)

    def open_sheet(self, spreadsheet_id: str, worksheet_name: str):
        sh = self.gc.open_by_key(spreadsheet_id)
        try:
            ws = sh.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=worksheet_name, rows=1000, cols=30)
        return ws

    def read_sheet_tail(self, spreadsheet_id: str, worksheet_name: str, n_rows: int = 2000) -> pd.DataFrame:
        ws = self.open_sheet(spreadsheet_id, worksheet_name)
        df = get_as_dataframe(ws, evaluate_formulas=True, header=0)
        df = df.dropna(how='all')
        if len(df) > n_rows:
            df = df.tail(n_rows)
        return df

    def read_sheet_all(self, spreadsheet_id: str, worksheet_name: str) -> pd.DataFrame:
        ws = self.open_sheet(spreadsheet_id, worksheet_name)
        df = get_as_dataframe(ws, evaluate_formulas=True, header=0)
        return df.dropna(how='all')

    def append_rows(self, spreadsheet_id: str, worksheet_name: str, df: pd.DataFrame):
        ws = self.open_sheet(spreadsheet_id, worksheet_name)
        existing = get_as_dataframe(ws, evaluate_formulas=True, header=0)
        existing = existing.dropna(how='all')
        out = pd.concat([existing, df], ignore_index=True)
        set_with_dataframe(ws, out)

    def upload_to_drive(self, folder_id: str, local_path: str, remote_name: str):
        file = self.drive.CreateFile({'parents': [{'id': folder_id}], 'title': remote_name})
        file.SetContentFile(local_path)
        file.Upload()
        return file['id']
