import mpv


class VideoPlayer:

    def __init__(self):
        self.player: mpv.MPV | None = None

    def open_file(self) -> bool:
        try:
            self.stop()

            self.player = mpv.MPV(
                vo='gpu',
                ytdl=False,
            )
            return True
        except Exception as e:
            print(f"Error opening file: {e}")
            return False

    def get_fps(self) -> float:
        """Returns the video's frames per second."""
        return 30.0

    def is_playing(self) -> bool:
        """Check if media is currently playing."""
        return self.player is not None

    def play(self, filepath: str):
        """Start playback."""
        if self.player:
            self.player.play(filepath)

    def pause(self):
        """Pause playback."""
        if self.player:
            self.player.pause = True

    def stop(self):
        """Stop playback and release resources."""
        if self.player:
            self.player.terminate()
            self.player = None

    def set_handle(self, window_id: int):
        """Set the window handle for video rendering."""
        if self.player:
            self.player.wid = str(window_id)

    def get_time(self) -> int:
        """Get current playback position in milliseconds."""
        if self.player:
            return int(self.player.time_pos * 1000) if self.player.time_pos else 0
        return 0

    def set_time(self, time_ms: int):
        """Set playback position in milliseconds."""
        if self.player:
            self.player.time_pos = time_ms / 1000.0

    def get_length(self) -> int:
        """Get media length in milliseconds."""
        if self.player:
            return int(self.player.duration * 1000) if self.player.duration else 0
        return 0

    def __del__(self):
        """Cleanup on destruction."""
        self.stop()
