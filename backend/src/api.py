import httpx
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
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
    poster_url = await tmdb_api.get_poster_url(movie['title'], movie['year'])
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
async def stream_gdrive_video(file_id: str, start_time: float = Query(0.0, alias="ss", description="Start time in seconds")):
    stream_info = movie_scanner.get_stream_info(file_id)
    if not stream_info:
        raise HTTPException(status_code=404, detail="Could not generate stream info from Google Drive.")

    async def robust_ffmpeg_streamer():
        # Format headers for FFmpeg
        headers_str = "".join([f"{k}: {v}\r\n" for k, v in stream_info["headers"].items()])
        
        # FFmpeg command with native URL and seek support
        ffmpeg_cmd = [
            'ffmpeg',
            '-headers', headers_str,
            '-ss', str(start_time),  # Fast seek BEFORE input
            '-i', stream_info["url"],
            '-vcodec', 'h264_videotoolbox',
            '-acodec', 'aac',
            '-b:v', '4M',            # Set a reasonable bitrate for performance
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-pix_fmt', 'yuv420p',
            # Use fragmented MP4 for better streaming and seeking
            '-movflags', 'frag_keyframe+empty_moov+default_base_moof',
            '-f', 'mp4',
            '-loglevel', 'error',
            'pipe:1'
        ]

        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            # Read transcoded data from FFmpeg's stdout and yield to the client
            while True:
                chunk = await process.stdout.read(65536) # Increased chunk size for better throughput
                if not chunk:
                    break
                yield chunk
        
        except Exception as e:
            print(f"Streaming yield error: {e}")

        finally:
            if process.returncode is None:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
            
            stderr_output = await process.stderr.read()
            if stderr_output:
                print(f"FFmpeg stderr: {stderr_output.decode()}")
            
            await process.wait()

    return StreamingResponse(robust_ffmpeg_streamer(), media_type="video/mp4")

@app.get("/movie/{title}/poster", response_model=Dict)
async def get_movie_poster(title: str, year: Optional[str] = Query(None, description="Optional release year of the movie")):
    """
    Get the poster URL for a given movie title and optional year.
    """
    poster_url = await tmdb_api.get_poster_url(title, year)
    if not poster_url:
        # Fallback to a placeholder instead of raising 404 to keep the frontend smooth
        return {"title": title, "year": year, "poster_url": "https://via.placeholder.com/300x450?text=No+Poster"}
    return {"title": title, "year": year, "poster_url": poster_url}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
