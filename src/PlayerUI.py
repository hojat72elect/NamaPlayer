import tkinter as tk
from tkinter import filedialog
from VideoPlayer import VideoPlayer

class PlayerUI:
    """Controls the UI of the player."""

    def __init__(self):
        self.player = VideoPlayer()
        self.root = tk.Tk()
        self.root.title("NamaPlayer")

        # Video will be rendered into this frame
        self.video_frame = tk.Frame(self.root, width=800, height=600, bg="black")
        self.video_frame.pack()

        open_button = tk.Button(self.root, text="Open Video", command=self.open_file)
        open_button.pack()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def open_file(self):
        filepath = filedialog.askopenfilename()
        if not filepath:
            return

        if self.player.open_file():
            # Get the window handle for the video frame
            self.root.update_idletasks()
            window_handle = self.video_frame.winfo_id()
            self.player.set_handle(window_handle)
            self.player.play(filepath)

    def on_closing(self):
        self.player.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()
