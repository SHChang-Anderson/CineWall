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
async def stream_gdrive_video(file_id: str):
    """
    Streams a Google Drive video by downloading it in chunks and feeding it to FFmpeg for on-the-fly transcoding.
    This provides a robust solution that avoids direct FFmpeg access to the source URL.
    """
    stream_info = movie_scanner.get_stream_info(file_id)
    if not stream_info:
        raise HTTPException(status_code=404, detail="Could not generate stream info from Google Drive.")

    async def robust_ffmpeg_streamer():
        # FFmpeg command now reads from stdin ('-i -')
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', '-',
            '-vcodec', 'h264_videotoolbox',
            '-acodec', 'aac',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-pix_fmt', 'yuv420p',
            '-movflags', 'frag_keyframe+empty_moov',
            '-f', 'mp4',
            '-loglevel', 'error',
            'pipe:1'
        ]

        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        downloader_task = None

        try:
            # Task 1: Asynchronously download from Google Drive and feed to FFmpeg's stdin
            async def download_and_feed():
                try:
                    # Use the URL and Headers from get_stream_info
                    async with httpx.AsyncClient(timeout=None) as client:
                        async with client.stream("GET", stream_info["url"], headers=stream_info["headers"]) as response:
                            response.raise_for_status()
                            async for chunk in response.aiter_bytes():
                                if process.stdin.is_closing():
                                    break
                                try:
                                    process.stdin.write(chunk)
                                    await process.stdin.drain()
                                except (BrokenPipeError, ConnectionResetError):
                                    # This can happen if the client closes the connection
                                    break
                except Exception as e:
                    print(f"Downloader task error: {e}")
                finally:
                    if not process.stdin.is_closing():
                        process.stdin.close()

            downloader_task = asyncio.create_task(download_and_feed())

            # Task 2: Read transcoded data from FFmpeg's stdout and yield to the client
            while True:
                chunk = await process.stdout.read(4096)
                if not chunk:
                    break
                yield chunk
        
        except Exception as e:
            print(f"Streaming yield error: {e}")

        finally:
            # Final cleanup
            if downloader_task and not downloader_task.done():
                downloader_task.cancel()
            if process.returncode is None:
                process.terminate()
            
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
    poster_url = tmdb_api.get_poster_url(title, year)
    if not poster_url:
        raise HTTPException(status_code=404, detail=f"No poster found for movie '{title}' (Year: {year})")
    return {"title": title, "year": year, "poster_url": poster_url}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
