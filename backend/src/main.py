#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path
from typing import List, Dict
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QScrollArea, QLabel, QGridLayout,
                             QPushButton, QLineEdit, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt

from movie_scanner import MovieScanner
from tmdb_api import TMDbAPI
from poster_widget import PosterWidget
from mpv_player import MPVPlayer


class CineWallApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CineWall 🎬")
        self.setGeometry(100, 100, 1200, 800)

        self.movie_scanner = MovieScanner()
        self.tmdb_api = TMDbAPI()
        self.mpv_player = MPVPlayer()

        self.movies: List[Dict] = []
        self.poster_widgets: List[PosterWidget] = []

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Header with folder selection
        header_layout = QHBoxLayout()

        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Select movie folder...")
        header_layout.addWidget(self.folder_input)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_folder)
        header_layout.addWidget(browse_btn)

        scan_btn = QPushButton("Scan Movies")
        scan_btn.clicked.connect(self.scan_movies)
        header_layout.addWidget(scan_btn)

        gdrive_scan_btn = QPushButton("Scan Google Drive")
        gdrive_scan_btn.clicked.connect(self.scan_gdrive)
        header_layout.addWidget(gdrive_scan_btn)

        layout.addLayout(header_layout)

        # Scroll area for poster grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.poster_container = QWidget()
        self.poster_grid = QGridLayout(self.poster_container)
        self.poster_grid.setSpacing(10)

        self.scroll_area.setWidget(self.poster_container)
        layout.addWidget(self.scroll_area)

        # Status bar
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Movie Folder")
        if folder:
            self.folder_input.setText(folder)

    def scan_gdrive(self):
        self.folder_input.setText("gdrive")
        self.scan_movies()

    def scan_movies(self):
        folder_path = self.folder_input.text().strip()
        if not folder_path or (folder_path.lower() != 'gdrive' and not os.path.exists(folder_path)):
            QMessageBox.warning(self, "Warning", "Please select a valid folder or use the Google Drive scan.")
            return

        self.status_label.setText("Scanning movies...")
        QApplication.processEvents()
        self.movies = self.movie_scanner.scan_folder(folder_path)

        if not self.movies:
            QMessageBox.information(self, "Info", "No movies found.")
            self.status_label.setText("No movies found")
            return

        self.status_label.setText(f"Found {len(self.movies)} movies. Fetching posters...")
        self.fetch_posters()

    def fetch_posters(self):
        for i, movie in enumerate(self.movies):
            poster_url = self.tmdb_api.get_poster_url(movie['title'], movie.get('year'))
            movie['poster_url'] = poster_url

            self.status_label.setText(f"Fetching posters... ({i+1}/{len(self.movies)})")
            QApplication.processEvents()

        self.create_poster_grid()
        self.status_label.setText(f"Ready - {len(self.movies)} movies loaded")

    def create_poster_grid(self):
        # Clear existing widgets
        for widget in self.poster_widgets:
            widget.deleteLater()
        self.poster_widgets.clear()

        # Clear grid layout
        while self.poster_grid.count():
            item = self.poster_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add poster widgets to grid
        columns = 5
        for i, movie in enumerate(self.movies):
            row = i // columns
            col = i % columns

            poster_widget = PosterWidget(movie, self.play_movie)
            self.poster_widgets.append(poster_widget)
            self.poster_grid.addWidget(poster_widget, row, col)

    def play_movie(self, movie_path: str):
        # Check if the path is a local file or a GDrive ID
        if not os.path.exists(movie_path):
             QMessageBox.information(self, "Info", "Playing from Google Drive is not yet implemented.")
             return
        try:
            self.mpv_player.play(movie_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to play movie: {str(e)}")

    def load_settings(self):
        settings_file = Path("settings.json")
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    if 'last_folder' in settings:
                        self.folder_input.setText(settings['last_folder'])
            except Exception:
                pass

    def save_settings(self):
        settings = {
            'last_folder': self.folder_input.text()
        }
        try:
            with open("settings.json", 'w') as f:
                json.dump(settings, f)
        except Exception:
            pass

    def closeEvent(self, event):
        self.save_settings()
        self.mpv_player.cleanup()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = CineWallApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()