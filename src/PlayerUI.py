import tkinter as tk
from tkinter import filedialog
from VideoPlayer import VideoPlayer


class PlayerUI:
    """Controls the UI of the player and how it looks like."""

    def __init__(self):
        self.player = VideoPlayer()
        self.ui_root = tk.Tk()
        self.ui_root.title("NamaPlayer")

        # Create a frame for VLC to render into
        self.video_frame = tk.Frame(self.ui_root, width=800, height=600, bg="black")
        self.video_frame.pack()

        open_button = tk.Button(self.ui_root, text="Open Video", command=self.open_file)
        open_button.pack()

        self.ui_root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def open_file(self):
        filepath = filedialog.askopenfilename()
        if not filepath:
            return

        if self.player.open_file(filepath):
            # Get the window handle for the video frame
            # On Windows, we need to get the HWND
            self.ui_root.update_idletasks()
            hwnd = self.video_frame.winfo_id()
            self.player.set_hwnd(hwnd)
            self.player.play(filepath)

    def on_closing(self):
        self.player.stop()
        self.ui_root.destroy()

    def run(self):
        self.ui_root.mainloop()
