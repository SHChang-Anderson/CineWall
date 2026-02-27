import os
import re
from pathlib import Path
from typing import List, Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


class MovieScanner:
    def __init__(self):
        self.video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}

    def _get_gdrive_service(self):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return build('drive', 'v3', credentials=creds)

    def _get_folder_id(self, service, folder_name: str) -> Optional[str]:
        """Find the ID of a folder by its name."""
        try:
            query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            files = response.get('files', [])
            if files:
                return files[0].get('id')
        except Exception as e:
            print(f"[GDrive] Error finding folder '{folder_name}': {e}")
        return None

    def scan_google_drive(self, target_folder: str = "movie") -> List[Dict]:
        movies = []
        print(f"[GDrive] Starting scan in folder: {target_folder}...")
        try:
            service = self._get_gdrive_service()
            creds = service._http.credentials
            if not creds.token:
                creds.refresh(Request())
            access_token = creds.token

            # 1. Find the target folder ID
            folder_id = self._get_folder_id(service, target_folder)
            
            # 2. Build the query: Search within the folder or everywhere if not found
            if folder_id:
                query = f"'{folder_id}' in parents and mimeType contains 'video/' and trashed = false"
                print(f"[GDrive] Found '{target_folder}' folder ID: {folder_id}")
            else:
                query = "mimeType contains 'video/' and trashed = false"
                print(f"[GDrive] Warning: Folder '{target_folder}' not found. Scanning entire drive.")

            page_token = None
            while True:
                response = service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, size, mimeType)',
                    pageToken=page_token
                ).execute()

                found_files = response.get('files', [])
                for file in found_files:
                    file_name = file.get('name')
                    file_id = file.get('id')
                    print(f"[GDrive] Found file: {file_name} (ID: {file_id})")
                    
                    # Ensure it's a video type we care about (especially .mkv)
                    ext = Path(file_name).suffix.lower()
                    if ext not in self.video_extensions:
                        continue

                    title, year = self.parse_filename(Path(file_name).stem)
                    if not title:
                        title = Path(file_name).stem

                    stream_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&access_token={access_token}"
                    movies.append({
                        'id': file_id,
                        'title': title,
                        'year': year,
                        'file_path': file_id,
                        'file_size': file.get('size', 0),
                        'extension': ext,
                        'stream_url': stream_url
                    })
                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
        except Exception as e:
            print(f"[GDrive] Unexpected error: {e}")
            return []

        print(f"[GDrive] Scan complete. Total: {len(movies)}")
        return sorted(movies, key=lambda x: x['title'])

    def get_stream_url(self, file_id: str) -> Optional[str]:
        try:
            service = self._get_gdrive_service()
            creds = service._http.credentials
            if not creds.valid:
                creds.refresh(Request())
            return f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&access_token={creds.token}"
        except Exception:
            return None

    def scan_folder(self, folder_path: str) -> List[Dict]:
        if folder_path.lower().strip() == 'gdrive':
            return self.scan_google_drive()

        movies = []
        folder = Path(folder_path)

        if not folder.exists() or not folder.is_dir():
            return movies

        for file_path in folder.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.video_extensions:
                movie_info = self.extract_movie_info(file_path)
                if movie_info:
                    movies.append(movie_info)

        return sorted(movies, key=lambda x: x['title'])

    def extract_movie_info(self, file_path: Path) -> Optional[Dict]:
        try:
            filename = file_path.stem
            title, year = self.parse_filename(filename)

            return {
                'title': title,
                'year': year,
                'file_path': str(file_path),
                'file_size': file_path.stat().st_size,
                'extension': file_path.suffix.lower()
            }
        except Exception:
            return None

    def parse_filename(self, filename: str) -> tuple:
        # Remove common tags and quality indicators
        clean_name = re.sub(r'\[(.*?)\]', '', filename)
        clean_name = re.sub(r'\((.*?)\)', '', clean_name)
        clean_name = re.sub(r'\b(1080p|720p|480p|4K|BluRay|WEB-DL|DVDRip|CAMRip|HDTV)\b', '', clean_name, flags=re.IGNORECASE)
        clean_name = re.sub(r'\b(x264|x265|h264|h265|AAC|AC3|DTS)\b', '', clean_name, flags=re.IGNORECASE)
        clean_name = re.sub(r'\b(YIFY|RARBG|aXXo|FXG|CHD|EVO)\b', '', clean_name, flags=re.IGNORECASE)

        # Extract year
        year_match = re.search(r'\b(19|20)\d{2}\b', filename)
        year = year_match.group() if year_match else None

        # Clean up title
        if year:
            clean_name = re.sub(rf'\b{year}\b', '', clean_name)

        # Replace dots, underscores, and multiple spaces with single spaces
        clean_name = re.sub(r'[._]', ' ', clean_name)
        clean_name = re.sub(r'\s+', ' ', clean_name)
        clean_name = clean_name.strip()

        # Remove common prefixes/suffixes
        clean_name = re.sub(r'^(the|a|an)\s+', '', clean_name, flags=re.IGNORECASE)

        return clean_name, year