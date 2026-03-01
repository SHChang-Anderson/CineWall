# CineWall 

**CineWall** is a lightweight poster-wall movie player and cloud-based media center. It scans your local or cloud folders (Google Drive), automatically fetches movie posters from [TMDb](https://www.themoviedb.org/), and provides an immersive viewing experience.

## New Design: CineWall Cloud
The project has been upgraded to a modern, API-driven architecture with a sleek, dark-themed interface inspired by modern streaming platforms.

### Key Features
- **Modern Web Interface:** Built with **React** or **NiceGUI** for a seamless, responsive experience.
- **FastAPI Backend:** A robust, high-performance API for scanning, streaming, and metadata retrieval.
- **Google Drive Integration:** Directly scan and stream movies from your Google Drive with on-the-fly transcoding using FFmpeg.
- **Smart Poster Fetching:** Automatically matches movies with high-quality posters from TMDb.
- **Cross-Platform:** Run as a desktop app (PyQt5) or a cloud service accessible via any web browser.


## Architecture
- **Backend:** Python, FastAPI, httpx, FFmpeg
- **Web UI (Option A):** React (located in `frontend/`)
- **Web UI (Option B):** NiceGUI (located in `backend/src/app.py`)
- **Desktop UI:** PyQt5 (located in `backend/src/main.py`)

---

## Installation & Setup

### 1. Requirements
- Python 3.9+
- [FFmpeg](https://ffmpeg.org/) (for cloud streaming)
- Node.js & npm (if using the React frontend)
- [MPV](https://mpv.io/) (for desktop player)

### 2. Install Dependencies
```bash
# Clone the repository
git clone https://github.com/<your-username>/CineWall.git
cd CineWall

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python packages
pip install -r backend/requirements.txt
```

### 3. Setup Frontend (Optional)
If you want to use the React frontend:
```bash
cd frontend
npm install
```

---

## How to Run

### Option 1: Modern Cloud UI (NiceGUI)
The fastest way to experience the new dark-themed design.
```bash
cd backend/src
python app.py
```
Visit `http://localhost:8080` in your browser.

### 🔹 Option 2: Full Stack (FastAPI + React)
Best for a production-like web experience.
```bash
# Terminal 1: Start Backend API
cd backend/src
python api.py

# Terminal 2: Start React Frontend
cd frontend
npm start
```
Visit `http://localhost:3000` in your browser.

### Option 3: Classic Desktop App (PyQt5)
```bash
cd backend/src
python main.py
```

---

## Configuration
Update your TMDb API key and other settings in `backend/config/.tmdb_config.json` (or via environment variables).

## 📄 License
MIT License
