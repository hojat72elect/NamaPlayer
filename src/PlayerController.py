import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import cv2


class PlayerController:
    def __init__(self):
        self.ui_root = tk.Tk()
        self.ui_root.title("NamaPlayer")
        self.video_label = tk.Label(self.ui_root)
        self.video_label.pack()

        self.player = None
        self.after_id = None

        open_button = tk.Button(self.ui_root, text="Open Video", command=self.open_file)
        open_button.pack()

        self.ui_root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.ui_root.mainloop()

    def open_file(self):
        filepath = filedialog.askopenfilename()
        if not filepath:
            return

        if self.player:
            self.player.release()
            if self.after_id:
                self.video_label.after_cancel(self.after_id)

        self.player = cv2.VideoCapture(filepath)
        self.update_video()

    def update_video(self):
        if not self.player:
            return

        ret, frame = self.player.read()

        if not ret:
            self.player.release()
            self.player = None
            return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame_rgb.shape[:2]
        pil_img = Image.frombytes("RGB", (w, h), frame_rgb.tobytes())

        img_tk = ImageTk.PhotoImage(image=pil_img)
        self.video_label.config(image=img_tk)
        self.video_label.image = img_tk

        fps = self.player.get(cv2.CAP_PROP_FPS)
        delay = int(1_000 / fps) if fps > 0 else 30

        self.after_id = self.video_label.after(delay, self.update_video)

    def on_closing(self):
        if self.player:
            self.player.release()
        self.ui_root.destroy()
