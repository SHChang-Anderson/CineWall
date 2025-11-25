from fastapi import FastAPI, Query, HTTPException
from typing import List, Dict, Optional
from movie_scanner import MovieScanner
from tmdb_api import TMDbAPI
import uvicorn

app = FastAPI()

movie_scanner = MovieScanner()
tmdb_api = TMDbAPI()

@app.get("/")
async def read_root():
    return {"message": "Welcome to CineWall API"}

@app.get("/movies/local", response_model=List[Dict])
async def get_local_movies(folder_path: str = Query(..., description="Path to the local movie folder")):
    """
    Scan a local folder for movie files and return their information.
    """
    if not folder_path:
        raise HTTPException(status_code=400, detail="Folder path cannot be empty.")
    
    movies = movie_scanner.scan_folder(folder_path)
    if not movies:
        raise HTTPException(status_code=404, detail=f"No movies found in {folder_path}")
    
    return movies

@app.get("/movies/gdrive", response_model=List[Dict])
async def get_gdrive_movies():
    """
    Scan Google Drive for movie files and return their information.
    Authentication is handled via `credentials.json` and `token.json` files.
    """
    movies = movie_scanner.scan_google_drive()
    if not movies:
        raise HTTPException(status_code=404, detail="No movies found on Google Drive or an error occurred during scanning.")
    return movies

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
