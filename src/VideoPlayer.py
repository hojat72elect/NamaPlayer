import mpv


class VideoPlayer:
    def __init__(self):
        self.player: mpv.MPV | None = None

    def open_file(self) -> bool:
        try:
            self.stop()

            self.player = mpv.MPV(
                vo="gpu",
                ytdl=False,
            )
            return True
        except Exception as e:
            print(f"Error opening file: {e}")
            return False

    def play(self, filepath: str):
        """Start playback."""
        if self.player:
            self.player.play(filepath)

    def stop(self):
        """Stop playback and release resources."""
        if self.player:
            self.player.terminate()
            self.player = None

    def set_handle(self, window_id: int):
        """Set the window handle for video rendering."""
        if self.player:
            self.player.wid = str(window_id)

    def __del__(self):
        """Cleanup on destruction."""
        self.stop()
