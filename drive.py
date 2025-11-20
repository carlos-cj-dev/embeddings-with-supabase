import io
import os
from googleapiclient.discovery import build
from google.oauth2 import service_account
from docx import Document

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE = service_account.Credentials.from_service_account_file(
    "credentials.json", scopes=SCOPES
)

drive = build("drive", "v3", credentials=SERVICE)

def download_file(file_id):
    request = drive.files().export_media(fileId=file_id, mimeType='text/plain')
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    path = f"/tmp/{file_id}.txt"
    with open(path, "wb") as f:
        f.write(fh.getvalue())

    return path

def extract_text(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
