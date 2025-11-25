import os
import subprocess
import platform
from typing import Optional


class MPVPlayer:
    def __init__(self):
        self.mpv_process: Optional[subprocess.Popen] = None
        self.mpv_path = self.find_mpv()

    def find_mpv(self) -> Optional[str]:
        # Try to find mpv executable
        try:
            # Check if mpv is in PATH
            result = subprocess.run(['which', 'mpv'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        # Common installation paths for different platforms
        common_paths = []

        if platform.system() == "Darwin":  # macOS
            common_paths = [
                "/usr/local/bin/mpv",
                "/opt/homebrew/bin/mpv",
                "/Applications/mpv.app/Contents/MacOS/mpv"
            ]
        elif platform.system() == "Linux":
            common_paths = [
                "/usr/bin/mpv",
                "/usr/local/bin/mpv",
                "/snap/bin/mpv"
            ]
        elif platform.system() == "Windows":
            common_paths = [
                "C:\\Program Files\\mpv\\mpv.exe",
                "C:\\Program Files (x86)\\mpv\\mpv.exe",
                "mpv.exe"  # If in PATH
            ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        return None

    def play(self, video_path: str) -> bool:
        if not self.mpv_path:
            raise Exception("MPV player not found. Please install mpv.")

        if not os.path.exists(video_path):
            raise Exception(f"Video file not found: {video_path}")

        try:
            # Stop any currently playing video
            self.stop()

            # Start new mpv process
            mpv_args = [
                self.mpv_path,
                video_path,
                "--fullscreen",
                "--osd-level=1",
                "--volume=50"
            ]

            self.mpv_process = subprocess.Popen(
                mpv_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            return True

        except Exception as e:
            raise Exception(f"Failed to start mpv: {str(e)}")

    def stop(self):
        if self.mpv_process and self.mpv_process.poll() is None:
            try:
                self.mpv_process.terminate()
                self.mpv_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.mpv_process.kill()
            except Exception:
                pass
            finally:
                self.mpv_process = None

    def is_playing(self) -> bool:
        return self.mpv_process is not None and self.mpv_process.poll() is None

    def cleanup(self):
        self.stop()