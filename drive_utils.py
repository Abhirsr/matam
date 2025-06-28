import os
import re
import gdown
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_CREDS_FILE")

def upload_to_drive(folder_name, file_paths):
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    drive_service = build('drive', 'v3', credentials=creds)

    # Create folder in Drive
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
    folder_id = folder.get('id')

    # Upload each file
    for file_path in file_paths:
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_path, resumable=True)
        drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    # Make folder public
    drive_service.permissions().create(
        fileId=folder_id,
        body={'type': 'anyone', 'role': 'reader'},
        fields='id'
    ).execute()

    # Return shareable link
    return f"https://drive.google.com/drive/folders/{folder_id}?usp=sharing"

def download_drive_folder(drive_link, dest_folder):
    """
    Downloads all files from a public Google Drive folder using gdown.
    `drive_link` should be a full link to a Google Drive folder.
    Files are saved in `dest_folder`.
    """
    try:
        # Extract folder ID from the URL
        match = re.search(r'/folders/([a-zA-Z0-9_-]+)', drive_link)
        if not match:
            return False, "Invalid Google Drive folder link."

        folder_id = match.group(1)

        # Ensure destination folder exists
        os.makedirs(dest_folder, exist_ok=True)

        # Download folder using gdown
        gdown.download_folder(id=folder_id, output=dest_folder, quiet=False, use_cookies=False)

        return True, "Downloaded successfully."
    except Exception as e:
        return False, str(e)