import tkinter as tk
from tkinter import filedialog

from PIL import Image, ImageTk
import cv2

root = tk.Tk()
root.title("NamaPlayer")

video_label = tk.Label(root)
video_label.pack()

player = None
after_id = None


def open_file():
    global player, after_id

    filepath = filedialog.askopenfilename()
    if not filepath:
        return

    if player:
        player.release()
        if after_id:
            video_label.after_cancel(after_id)

    player = cv2.VideoCapture(filepath)
    update_video()


def update_video():
    global player, after_id
    if not player:
        return

    ret, frame = player.read()

    if not ret:
        player.release()
        player = None
        return

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w = frame_rgb.shape[:2]
    pil_img = Image.frombytes("RGB", (w, h), frame_rgb.tobytes())

    img_tk = ImageTk.PhotoImage(image=pil_img)
    video_label.config(image=img_tk)
    video_label.image = img_tk

    fps = player.get(cv2.CAP_PROP_FPS)
    delay = int(1000 / fps) if fps > 0 else 30

    after_id = video_label.after(delay, update_video)


def on_closing():
    global player
    if player:
        player.release()
    root.destroy()


open_button = tk.Button(root, text="Open Video", command=open_file)
open_button.pack()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
