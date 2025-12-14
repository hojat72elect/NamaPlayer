import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
from ffpyplayer.player import MediaPlayer
import os

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
        player.close_player()
        if after_id:
            video_label.after_cancel(after_id)

    ff_opts = {'out_fmt': 'rgb24'}
    player = MediaPlayer(filepath, ff_opts=ff_opts)
    update_video()

def update_video():
    global player, after_id
    if not player:
        return

    frame, val = player.get_frame()
    
    if val == 'eof':
        player.close_player()
        player = None
        return

    delay = 1
    if frame is not None:
        img, t = frame
        
        w, h = img.get_size()
        img_data = img.to_bytearray()[0]
        pil_img = Image.frombytes("RGB", (w, h), bytes(img_data))

        img_tk = ImageTk.PhotoImage(image=pil_img)
        video_label.config(image=img_tk)
        video_label.image = img_tk
    else:
        delay = int(val * 1000)
        if delay == 0:
            delay = 1
    
    after_id = video_label.after(delay, update_video)

def on_closing():
    global player
    if player:
        player.close_player()
    root.destroy()

open_button = tk.Button(root, text="Open Video", command=open_file)
open_button.pack()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
