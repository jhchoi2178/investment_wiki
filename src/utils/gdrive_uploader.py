"""
Google Drive API(서비스 계정)를 이용해 수집된 CSV 파일을 data/weekly 폴더에 업로드한다.
"""

import json
import os
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]


def get_drive_service():
    """GDRIVE_CREDENTIALS(OAuth2 JSON)로 Google Drive API 클라이언트를 생성한다."""
    creds_json = os.getenv("GDRIVE_CREDENTIALS")
    if not creds_json:
        raise ValueError("GDRIVE_CREDENTIALS 환경변수가 설정되지 않았습니다.")
    info = json.loads(creds_json)
    creds = Credentials.from_authorized_user_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def get_or_create_folder(service, name: str, parent_id: str) -> str:
    """parent_id 하위에 name 폴더가 있으면 ID를 반환하고, 없으면 새로 생성한다."""
    query = (
        f"name = '{name}' and '{parent_id}' in parents "
        "and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    res = service.files().list(q=query, fields="files(id, name)").execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]

    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def upload_csv_files(local_dir: Path, data_folder_id: str, subfolder: str = "weekly") -> None:
    """local_dir 내 모든 CSV 파일을 Drive data/{subfolder} 폴더에 업로드(덮어쓰기)한다."""
    service = get_drive_service()
    target_folder_id = get_or_create_folder(service, subfolder, data_folder_id)

    for csv_path in sorted(local_dir.glob("*.csv")):
        query = f"name = '{csv_path.name}' and '{target_folder_id}' in parents and trashed = false"
        existing = service.files().list(q=query, fields="files(id)").execute().get("files", [])
        media = MediaFileUpload(str(csv_path), mimetype="text/csv", resumable=True)

        if existing:
            file_id = existing[0]["id"]
            service.files().update(fileId=file_id, media_body=media).execute()
            print(f"[OK] Updated on Drive: {subfolder}/{csv_path.name}")
        else:
            meta = {"name": csv_path.name, "parents": [target_folder_id]}
            service.files().create(body=meta, media_body=media, fields="id").execute()
            print(f"[OK] Uploaded to Drive: {subfolder}/{csv_path.name}")


if __name__ == "__main__":
    folder_id = os.getenv("GDRIVE_DATA_FOLDER_ID", "1hoAu_lKrzy8TXWZZCWnAZLvDVuSsAyJf")
    upload_csv_files(Path("data"), folder_id)
