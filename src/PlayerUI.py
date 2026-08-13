import tkinter as tk
from tkinter import filedialog
from PIL import ImageTk
from PlayerController import PlayerController


class PlayerUI:
    def __init__(self):
        self.controller = PlayerController()
        self.ui_root = tk.Tk()
        self.ui_root.title("NamaPlayer")

        self.video_label = tk.Label(self.ui_root)
        self.video_label.pack()

        self.after_id = None

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

        if self.controller.open_file(filepath):
            self.update_video()

    def update_video(self):
        if not self.controller.is_playing():
            return

        frame = self.controller.get_frame()
        if frame is None:
            return

        img_tk = ImageTk.PhotoImage(image=frame)
        self.video_label.config(image=img_tk)
        self.video_label.image = img_tk

        fps = self.controller.get_fps()
        delay = int(1_000 / fps) if fps > 0 else 30

        self.after_id = self.video_label.after(delay, self.update_video)

    def on_closing(self):
        if self.after_id:
            self.video_label.after_cancel(self.after_id)
        self.controller.stop()
        self.ui_root.destroy()

    def run(self):
        self.ui_root.mainloop()
