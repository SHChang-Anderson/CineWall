from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from movie_scanner import MovieScanner
from tmdb_api import TMDbAPI
import uvicorn
import asyncio

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

movie_scanner = MovieScanner()
tmdb_api = TMDbAPI()

@app.get("/")
async def read_root():
    return {"message": "Welcome to CineWall API"}

async def fetch_poster_for_movie(movie: Dict):
    poster_url = tmdb_api.get_poster_url(movie['title'], movie['year'])
    if not poster_url:
        poster_url = 'https://via.placeholder.com/300x450?text=No+Poster'
    movie['poster_url'] = poster_url
    return movie

@app.get("/movies/gdrive", response_model=List[Dict])
async def get_gdrive_movies(folder: str = Query("movie", description="The folder to scan on Google Drive")):
    """
    Scan a specific Google Drive folder for movie files and return their information including posters.
    """
    movies = movie_scanner.scan_google_drive(target_folder=folder)
    if not movies:
        return [] # Return empty list if no movies found
    
    # Efficiently fetch posters
    movies_with_posters = await asyncio.gather(*[fetch_poster_for_movie(m) for m in movies])
    return movies_with_posters

@app.get("/stream/{file_id}")
async def get_stream_url(file_id: str):
    """
    Returns the direct stream URL for a given Google Drive file ID.
    """
    stream_url = movie_scanner.get_stream_url(file_id)
    if not stream_url:
        raise HTTPException(status_code=404, detail="Could not generate stream URL.")
    return {"stream_url": stream_url}

@app.get("/movie/{title}/poster", response_model=Dict)
async def get_movie_poster(title: str, year: Optional[str] = Query(None, description="Optional release year of the movie")):
    """
    Get the poster URL for a given movie title and optional year.
    """
    poster_url = tmdb_api.get_poster_url(title, year)
    if not poster_url:
        raise HTTPException(status_code=404, detail=f"No poster found for movie '{title}' (Year: {year})")
    return {"title": title, "year": year, "poster_url": poster_url}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
