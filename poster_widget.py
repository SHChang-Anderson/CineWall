import os
from pathlib import Path
from typing import Callable, Dict
import requests
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont


class PosterDownloadThread(QThread):
    poster_downloaded = pyqtSignal(str, str)  # poster_path, movie_title

    def __init__(self, poster_url: str, poster_path: str, movie_title: str):
        super().__init__()
        self.poster_url = poster_url
        self.poster_path = poster_path
        self.movie_title = movie_title

    def run(self):
        try:
            response = requests.get(self.poster_url, timeout=30)
            response.raise_for_status()

            with open(self.poster_path, 'wb') as f:
                f.write(response.content)

            self.poster_downloaded.emit(self.poster_path, self.movie_title)
        except Exception as e:
            print(f"Error downloading poster for {self.movie_title}: {e}")


class PosterWidget(QWidget):
    def __init__(self, movie: Dict, play_callback: Callable[[str], None]):
        super().__init__()
        self.movie = movie
        self.play_callback = play_callback

        self.setFixedSize(200, 320)
        self.setStyleSheet("""
            PosterWidget {
                background-color: #2b2b2b;
                border: 2px solid #444;
                border-radius: 8px;
            }
            PosterWidget:hover {
                border-color: #666;
                background-color: #333;
            }
        """)

        self.init_ui()
        self.load_poster()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Poster image
        self.poster_label = QLabel()
        self.poster_label.setFixedSize(190, 280)
        self.poster_label.setAlignment(Qt.AlignCenter)
        self.poster_label.setStyleSheet("""
            QLabel {
                background-color: #444;
                border: 1px solid #666;
                border-radius: 4px;
                color: white;
            }
        """)
        self.poster_label.setText("Loading...")
        layout.addWidget(self.poster_label)

        # Movie title
        self.title_label = QLabel(self.movie['title'])
        self.title_label.setWordWrap(True)
        self.title_label.setMaximumHeight(30)
        self.title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 11px;
                background: transparent;
                border: none;
            }
        """)
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

    def load_poster(self):
        poster_dir = Path("posters")
        poster_dir.mkdir(exist_ok=True)

        # Create safe filename
        safe_title = "".join(c for c in self.movie['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        poster_filename = f"{safe_title}_{self.movie.get('year', 'unknown')}.jpg"
        poster_path = poster_dir / poster_filename

        if poster_path.exists():
            self.display_poster(str(poster_path))
        elif self.movie.get('poster_url'):
            self.download_poster(self.movie['poster_url'], str(poster_path))
        else:
            self.show_no_poster()

    def download_poster(self, poster_url: str, poster_path: str):
        self.download_thread = PosterDownloadThread(poster_url, poster_path, self.movie['title'])
        self.download_thread.poster_downloaded.connect(self.display_poster)
        self.download_thread.start()

    def display_poster(self, poster_path: str):
        try:
            pixmap = QPixmap(poster_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(190, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.poster_label.setPixmap(scaled_pixmap)
            else:
                self.show_no_poster()
        except Exception:
            self.show_no_poster()

    def show_no_poster(self):
        self.poster_label.setText("No Poster\nAvailable")
        self.poster_label.setStyleSheet("""
            QLabel {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                color: #aaa;
                font-size: 12px;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.play_callback(self.movie['file_path'])
        super().mousePressEvent(event)