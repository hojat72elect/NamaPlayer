import cv2
from PIL import Image
from typing import Optional


class PlayerController:
    def __init__(self):
        self.player: Optional[cv2.VideoCapture] = None

    def open_file(self, filepath: str) -> bool:
        """Open a video file for playback."""
        if self.player:
            self.player.release()

        self.player = cv2.VideoCapture(filepath)
        return self.player.isOpened()

    def get_frame(self) -> Optional[Image.Image]:
        """Read and return the next frame as a PIL Image."""
        if not self.player:
            return None

        ret, frame = self.player.read()

        if not ret:
            self.player.release()
            self.player = None
            return None

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame_rgb.shape[:2]
        pil_img = Image.frombytes("RGB", (w, h), frame_rgb.tobytes())
        return pil_img

    def get_fps(self) -> float:
        """Get the video's frames per second."""
        if not self.player:
            return 0.0
        return self.player.get(cv2.CAP_PROP_FPS)

    def is_playing(self) -> bool:
        """Check if a video is currently loaded and playing."""
        return self.player is not None and self.player.isOpened()

    def stop(self):
        """Stop video playback and release resources."""
        if self.player:
            self.player.release()
            self.player = None

    def __del__(self):
        """Cleanup when the object is destroyed."""
        self.stop()
