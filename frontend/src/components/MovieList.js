import React from 'react';

function MovieList({ movies }) {
  if (!movies || movies.length === 0) {
    return <p>No movies to display.</p>;
  }

  return (
    <div className="movie-list">
      {movies.map((movie) => (
        <div key={movie.file_path} className="movie-card">
          <img src={movie.poster_url} alt={movie.title} />
          <div className="movie-info">
            <h3>{movie.title}</h3>
            {movie.year && <p>({movie.year})</p>}
          </div>
        </div>
      ))}
    </div>
  );
}

export default MovieList;
