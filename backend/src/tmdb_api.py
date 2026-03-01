import httpx
import json
import asyncio
from typing import Optional
from pathlib import Path


class TMDbAPI:
    def __init__(self):
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p/w500"
        self.api_key = self.load_api_key()

    def load_api_key(self) -> Optional[str]:
        # Try to load API key from config file
        config_dir = Path(__file__).parent.parent / "config"
        config_file = config_dir / "tmdb_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    key = config.get('api_key')
                    if key and key != "YOUR_TMDB_API_KEY_HERE":
                        return key
            except Exception as e:
                print(f"[TMDB] Error reading config file: {e}")
        return None

    async def get_poster_url(self, title: str, year: Optional[str] = None) -> Optional[str]:
        if not self.api_key:
            return None

        try:
            # Search for the movie
            search_url = f"{self.base_url}/search/movie"
            params = {
                'api_key': self.api_key,
                'query': title,
                'language': 'zh-TW' 
            }

            if year:
                params['year'] = year

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(search_url, params=params)

                if response.status_code != 200:
                    return None

                data = response.json()
                results = data.get('results', [])

                if not results:
                    return None

                # Get the first result (most relevant)
                movie = results[0]
                poster_path = movie.get('poster_path')

                if poster_path:
                    url = f"{self.image_base_url}{poster_path}"
                    return url

        except Exception as e:
            print(f"[TMDB] Unexpected error fetching poster for '{title}': {e}")

        return None