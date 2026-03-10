from __future__ import annotations

import io
import os
from typing import Optional

from googleapiclient.discovery import build  # type: ignore[import]
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload  # type: ignore[import]
from google.oauth2 import service_account  # type: ignore[import]
import google.auth  # type: ignore[import]


SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_drive_service():
    """
    Создаёт клиент Google Drive.

    Способы аутентификации:
    - GOOGLE_SERVICE_ACCOUNT_FILE — путь к service account JSON.
    - либо application default credentials (GOOGLE_APPLICATION_CREDENTIALS и т.п.).
    """
    sa_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    if sa_path:
        creds = service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)
    else:
        creds, _ = google.auth.default(scopes=SCOPES)

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
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )
    return created["id"]


def download_file_by_name(folder_id: str, file_name: str, local_path: str) -> None:
    """
    Находит файл по имени в указанной папке и скачивает его в local_path.
    Если файл не найден — бросает исключение.
    """
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

