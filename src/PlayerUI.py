import tkinter as tk
from tkinter import filedialog
from PIL import ImageTk
from VideoPlayer import VideoPlayer


class PlayerUI:
    """Controls the UI of the player and how it looks like."""

    def __init__(self):
        self.player = VideoPlayer()
        self.ui_root = tk.Tk()
        self.ui_root.title("NamaPlayer")

        self.video_label = tk.Label(self.ui_root)
        self.video_label.pack()

        self.after_id = None
        self.current_image = None

        open_button = tk.Button(self.ui_root, text="Open Video", command=self.open_file)
        open_button.pack()

        self.ui_root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def open_file(self):
        filepath = filedialog.askopenfilename()
        if not filepath:
            return

        if self.after_id:
            self.video_label.after_cancel(self.after_id)
            self.after_id = None

        if self.player.open_file(filepath):
            self.update_video()

    def update_video(self):
        if not self.player.is_playing():
            return

        frame = self.player.get_frame()
        if frame is None:
            return

        img_tk = ImageTk.PhotoImage(image=frame)
        self.video_label.config(image=img_tk)
        self.video_label.image = img_tk  # do not remove or change this line, we need to have it because of the GC issues

        fps = self.player.get_fps()
        delay = int(1_000 / fps) if fps > 0 else 30

        self.after_id = self.video_label.after(delay, self.update_video)

    def on_closing(self):
        if self.after_id:
            self.video_label.after_cancel(self.after_id)
        self.player.stop()
        self.ui_root.destroy()

    def run(self):
        self.ui_root.mainloop()
