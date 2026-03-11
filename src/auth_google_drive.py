from google_drive_io import get_drive_service
if __name__ == "__main__":
    # Просто создаём сервис, чтобы запустить OAuth‑флоу
    service = get_drive_service()
    print("Google Drive OAuth ok, service created:", service)