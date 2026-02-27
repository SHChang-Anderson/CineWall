import requests
import json
from typing import Optional
from pathlib import Path


class TMDbAPI:
    def __init__(self):
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p/w500"
        self.api_key = self.load_api_key()

    def load_api_key(self) -> Optional[str]:
        # Try to load API key from config file
        config_file = Path(__file__).parent.parent / "config" / "tmdb_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    key = config.get('api_key')
                    if key and key != "YOUR_TMDB_API_KEY_HERE":
                        print(f"[TMDB] API Key loaded successfully: {key[:4]}****")
                        return key
            except Exception as e:
                print(f"[TMDB] Error reading config file: {e}")

        print("[TMDB] WARNING: No valid API Key found in tmdb_config.json")
        return None

    def get_poster_url(self, title: str, year: Optional[str] = None) -> Optional[str]:
        if not self.api_key or self.api_key == "YOUR_TMDB_API_KEY_HERE":
            print("[TMDB] Skipping poster fetch: Missing API Key")
            return None

        try:
            # Search for the movie
            search_url = f"{self.base_url}/search/movie"
            params = {
                'api_key': self.api_key,
                'query': title,
                'language': 'zh-TW' # 優先抓中文資訊
            }

            if year:
                params['year'] = year

            print(f"[TMDB] Searching for: {title} ({year or 'N/A'})...")
            response = requests.get(search_url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"[TMDB] API Error: {response.status_code} - {response.text}")
                return None

            data = response.json()
            results = data.get('results', [])

            if not results:
                print(f"[TMDB] No results found for '{title}'")
                return None

            # Get the first result (most relevant)
            movie = results[0]
            poster_path = movie.get('poster_path')

            if poster_path:
                url = f"{self.image_base_url}{poster_path}"
                print(f"[TMDB] Found poster: {url}")
                return url
            else:
                print(f"[TMDB] Movie found, but no poster_path available for '{title}'")

        except Exception as e:
            print(f"[TMDB] Unexpected error fetching poster for '{title}': {e}")

        return None

    def download_poster(self, poster_url: str, save_path: str) -> bool:
        try:
            response = requests.get(poster_url, timeout=30)
            response.raise_for_status()

            with open(save_path, 'wb') as f:
                f.write(response.content)

            return True
        except Exception as e:
            print(f"Error downloading poster: {e}")
            return False