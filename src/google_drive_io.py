from __future__ import annotations

import io
import os
from typing import Optional

from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import]
from google.oauth2.credentials import Credentials  # type: ignore[import]
from google.auth.transport.requests import Request  # type: ignore[import]
from google.auth.exceptions import RefreshError  # type: ignore[import]
from googleapiclient.discovery import build  # type: ignore[import]
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload  # type: ignore[import]


SCOPES = ["https://www.googleapis.com/auth/drive.file"]

CREDENTIALS_FILE = os.getenv("GOOGLE_OAUTH_CLIENT_SECRETS_FILE", "credentials.json")
TOKEN_FILE = os.getenv("GOOGLE_OAUTH_TOKEN_FILE", "token.json")


def get_drive_service():
    creds: Optional[Credentials] = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError as e:
                raise RuntimeError(
                    "OAuth token refresh failed (invalid_grant). "
                    "Delete token.json and re-auth: run `python src/auth_google_drive.py` on the host."
                ) from e
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES,
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return build("drive", "v3", credentials=creds, cache_discovery=False)


def upload_file(local_path: str, folder_id: str, file_name: Optional[str] = None) -> str:
    """
    Загружает файл на Google Drive в указанную папку.
    Возвращает ID созданного файла.
    """
    if file_name is None:
        file_name = os.path.basename(local_path)

    service = get_drive_service()

    file_metadata = {"name": file_name, "parents": [folder_id]}
    media = MediaFileUpload(local_path, resumable=True)

    created = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id", supportsAllDrives=True)
        .execute()
    )
    return created["id"]


def download_file_by_name(folder_id: str, file_name: str, local_path: str) -> None:
    service = get_drive_service()

    query = (
        f"'{folder_id}' in parents and name = '{file_name}' and trashed = false"
    )

    resp = service.files().list(q=query, spaces="drive", fields="files(id, name)", pageSize=1).execute()
    files = resp.get("files", [])
    if not files:
        raise FileNotFoundError(f"File '{file_name}' not found in folder '{folder_id}'")

    file_id = files[0]["id"]

    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(local_path, mode="wb")
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

