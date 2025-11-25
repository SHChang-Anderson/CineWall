import React, { useState } from 'react';
import './App.css';
import ScannerControls from './components/ScannerControls';
import MovieList from './components/MovieList';

const API_BASE_URL = 'http://localhost:8000'; // Assuming FastAPI runs on this port

function App() {
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [statusMessage, setStatusMessage] = useState('Ready to scan!');

  const fetchMovies = async (endpoint, folderPath = null) => {
    setLoading(true);
    setError(null);
    setMovies([]); // Clear previous movies
    setStatusMessage('Scanning for movies...');

    try {
      let url = `${API_BASE_URL}${endpoint}`;
      if (folderPath) {
        url += `?folder_path=${encodeURIComponent(folderPath)}`;
      }
      
      const response = await fetch(url);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      let scannedMovies = await response.json();

      setStatusMessage(`Found ${scannedMovies.length} movies. Fetching posters...`);

      // Fetch posters for each movie
      const moviesWithPosters = await Promise.all(
        scannedMovies.map(async (movie) => {
          try {
            const posterResponse = await fetch(
              `${API_BASE_URL}/movie/${encodeURIComponent(movie.title)}/poster?year=${movie.year || ''}`
            );
            if (posterResponse.ok) {
              const posterData = await posterResponse.json();
              return { ...movie, poster_url: posterData.poster_url };
            } else {
              // If poster not found, return movie with a placeholder or default
              return { ...movie, poster_url: 'https://via.placeholder.com/150x225?text=No+Poster' };
            }
          } catch (posterError) {
            console.error('Error fetching poster for', movie.title, posterError);
            return { ...movie, poster_url: 'https://via.placeholder.com/150x225?text=Error' };
          }
        })
      );
      setMovies(moviesWithPosters);
      setStatusMessage(`Successfully loaded ${moviesWithPosters.length} movies.`);

    } catch (err) {
      setError(err.message);
      setStatusMessage(`Error: ${err.message}`);
      console.error('Fetch movies error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleScanLocal = (folderPath) => {
    fetchMovies('/movies/local', folderPath);
  };

  const handleScanGoogleDrive = () => {
    fetchMovies('/movies/gdrive');
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>CineWall Web</h1>
      </header>
      <main className="App-main">
        <ScannerControls
          onScanLocal={handleScanLocal}
          onScanGoogleDrive={handleScanGoogleDrive}
          loading={loading}
        />
        {statusMessage && <p className="status-message">{statusMessage}</p>}
        {error && <p style={{ color: 'red' }}>Error: {error}</p>}
        <MovieList movies={movies} />
      </main>
    </div>
  );
}

export default App;
