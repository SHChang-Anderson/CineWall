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

    def scan_google_drive(self) -> List[Dict]:
        movies = []
        try:
            service = self._get_gdrive_service()
            page_token = None
            while True:
                response = service.files().list(
                    q="mimeType contains 'video/'",
                    spaces='drive',
                    fields='nextPageToken, files(id, name, size)',
                    pageToken=page_token
                ).execute()

                for file in response.get('files', []):
                    title, year = self.parse_filename(Path(file.get('name')).stem)
                    if title:
                        movies.append({
                            'title': title,
                            'year': year,
                            'file_path': file.get('id'), # Store ID for GDrive files
                            'file_size': file.get('size', 0),
                            'extension': Path(file.get('name')).suffix.lower()
                        })
                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
        except HttpError as error:
            print(f'An error occurred: {error}')
            # Return empty list or handle error as needed
            return []
        except FileNotFoundError:
            print("Error: 'credentials.json' not found. Please follow the setup instructions.")
            return []

        return sorted(movies, key=lambda x: x['title'])

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