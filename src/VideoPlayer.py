import cv2
from PIL import Image
from typing import Optional
import pygame
import tempfile
import os
import subprocess
from typing import cast


class VideoPlayer:
    """Takes care of video and how to play it."""

    def __init__(self):
        self.player: Optional[cv2.VideoCapture] = None
        pygame.mixer.init()
        self.audio_file: Optional[str] = None
        self.temp_dir: Optional[tempfile.TemporaryDirectory] = None

    def open_file(self, filepath: str) -> bool:
        if self.player:
            self.player.release()

        self.stop_audio()

        self.player = cv2.VideoCapture(filepath)
        if self.player is None:
            return False
        else:
            if self.player.isOpened():
                self.extract_audio(filepath)
                return True
            return False

    def get_frame(self) -> Optional[Image.Image]:
        """Reads and returns the next frame of the video as a Pillow Image."""
        if not self.player:
            return None

        ret, frame = self.player.read()

        if not ret:
            self.player.release()
            self.player = None
            return None

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width = frame_rgb.shape[:2]
        pillow_image = Image.frombytes("RGB", (width, height), frame_rgb.tobytes())
        return pillow_image

    def get_fps(self) -> float:
        """Returns the video's frames per second."""
        if not self.player:
            return 0.0
        return self.player.get(cv2.CAP_PROP_FPS)

    def is_playing(self) -> bool:
        return self.player is not None and self.player.isOpened()

    def extract_audio(self, filepath: str):
        """Extract audio from video file to a temporary WAV file using ffmpeg."""
        try:
            if self.temp_dir:
                self.temp_dir.cleanup()

            self.temp_dir = tempfile.TemporaryDirectory()
            audio_path = os.path.join(self.temp_dir.name, "audio.wav")

            # Use ffmpeg to extract audio
            command = [
                'ffmpeg',
                '-i', filepath,
                '-vn',
                '-acodec', 'pcm_s16le',
                '-ar', '44100',
                '-ac', '2',
                audio_path,
                '-y'
            ]

            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode == 0 and os.path.exists(audio_path):
                self.audio_file = audio_path
            else:
                self.audio_file = None
        except FileNotFoundError:
            print("ffmpeg not found. Please install ffmpeg to enable audio playback.")
            self.audio_file = None
        except Exception as e:
            print(f"Error extracting audio: {e}")
            self.audio_file = None

    def play_audio(self):
        """Start playing the audio track."""
        if self.audio_file and os.path.exists(self.audio_file):
            pygame.mixer.music.load(self.audio_file)
            pygame.mixer.music.play()

    def stop_audio(self):
        """Stop audio playback and clean up temporary files."""
        pygame.mixer.music.stop()
        if self.temp_dir:
            self.temp_dir.cleanup()
            self.temp_dir = None
        self.audio_file = None

    def stop(self):
        """Stop video playback and release resources."""
        if self.player:
            self.player.release()
            self.player = None
        self.stop_audio()

    def __del__(self):
        """Cleanup just in case if an instance of this object was destroyed."""
        self.stop()
