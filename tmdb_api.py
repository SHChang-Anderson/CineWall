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
        config_file = Path("tmdb_config.json")
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('api_key')
            except Exception:
                pass

        # Create sample config file if it doesn't exist
        if not config_file.exists():
            sample_config = {
                "api_key": "YOUR_TMDB_API_KEY_HERE",
                "instructions": "Get your free API key from https://www.themoviedb.org/settings/api"
            }
            try:
                with open(config_file, 'w') as f:
                    json.dump(sample_config, f, indent=2)
            except Exception:
                pass

        return None

    def get_poster_url(self, title: str, year: Optional[str] = None) -> Optional[str]:
        if not self.api_key or self.api_key == "YOUR_TMDB_API_KEY_HERE":
            return None

        try:
            # Search for the movie
            search_url = f"{self.base_url}/search/movie"
            params = {
                'api_key': self.api_key,
                'query': title
            }

            if year:
                params['year'] = year

            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            results = data.get('results', [])

            if not results:
                return None

            # Get the first result (most relevant)
            movie = results[0]
            poster_path = movie.get('poster_path')

            if poster_path:
                return f"{self.image_base_url}{poster_path}"

        except Exception as e:
            print(f"Error fetching poster for '{title}': {e}")

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