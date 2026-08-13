import cv2
from PIL import Image
from typing import Optional


class VideoPlayer:
    """Takes care of video and how to play it."""

    def __init__(self):
        self.player: Optional[cv2.VideoCapture] = None

    def open_file(self, filepath: str) -> bool:
        if self.player:
            self.player.release()

        self.player = cv2.VideoCapture(filepath)
        if self.player is None:
            return False
        else:
            return self.player.isOpened()

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

    def stop(self):
        """Stop video playback and release resources."""
        if self.player:
            self.player.release()
            self.player = None

    def __del__(self):
        """Cleanup just in case if an instance of this object was destroyed."""
        self.stop()
