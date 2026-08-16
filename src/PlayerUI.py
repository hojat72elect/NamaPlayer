import tkinter as tk
from tkinter import filedialog

import ttkbootstrap as ttk

from VideoPlayer import VideoPlayer


class PlayerUI:
    """Controls the UI of the player."""

    def __init__(self):
        self.player = VideoPlayer()
        self.root = ttk.Window(themename="superhero")
        self.root.title("NamaPlayer")
        self.user_seeking = False
        self.is_fullscreen: bool = False

        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        media_menu = tk.Menu(menu_bar, tearoff=0)
        media_menu.add_command(label="Open file ...", command=self.open_file)
        menu_bar.add_cascade(label="Media", menu=media_menu)

        # Video will be rendered into this frame
        self.video_frame = ttk.Frame(self.root, width=800, height=600)
        self.video_frame.pack(fill=tk.BOTH, expand=True)
        self.video_frame.bind("<Double-Button-1>", self.toggle_fullscreen)

        # This frame will contain control buttons at the bottom of the player
        self.control_frame = ttk.Frame(self.root)
        self.control_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.play_pause_button = ttk.Button(self.control_frame, text="⏸", command=self.toggle_play_pause, width=3, bootstyle="primary")
        self.play_pause_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.seek_bar = ttk.Scale(self.control_frame, from_=0, to=100, orient=tk.HORIZONTAL, bootstyle="info")
        self.seek_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        self.seek_bar.bind("<ButtonPress-1>", self.on_seek_start)
        self.seek_bar.bind("<ButtonRelease-1>", self.on_seek_release)

        volume_label = ttk.Label(self.control_frame, text="Volume")
        volume_label.pack(side=tk.LEFT, padx=(5, 0), pady=5)

        self.volume_bar = ttk.Scale(self.control_frame, from_=0, to=100, orient=tk.HORIZONTAL, bootstyle="warning")
        self.volume_bar.pack(side=tk.LEFT, padx=5, pady=5)
        self.volume_bar.set(100)
        self.volume_bar.bind("<ButtonRelease-1>", self.on_volume_change)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind("<space>", lambda _: self.toggle_play_pause())
        self.root.bind("<Control-q>", lambda _: self.on_closing())

    def open_file(self):
        filepath = filedialog.askopenfilename()
        if not filepath:
            return

        if self.player.open_file():
            self.root.update_idletasks()
            window_handle = self.video_frame.winfo_id()
            self.player.set_handle(window_handle)
            self.player.play(filepath)

    def toggle_play_pause(self):
        self.player.toggle_pause()
        if self.player.player and self.player.player.pause:
            self.play_pause_button.config(text="▶")
        else:
            self.play_pause_button.config(text="⏸")

    def on_seek_start(self, _):
        self.user_seeking = True

    def on_seek_release(self, _):
        self.user_seeking = False
        if self.player.player:
            duration = self.player.player.duration
            if duration and duration > 0:
                value = self.seek_bar.get()
                position = (float(value) / 100) * duration
                self.player.player.time_pos = position

    def on_volume_change(self, _):
        volume = self.volume_bar.get()
        self.player.set_volume(volume)

    def toggle_fullscreen(self, _):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)

    def update_seek_bar(self):
        """Update seek bar's position to match current video position."""
        if self.player.player and not self.user_seeking:
            try:
                time_pos = self.player.player.time_pos
                duration = self.player.player.duration
                if time_pos is not None and duration is not None and duration > 0:
                    percentage = (time_pos / duration) * 100
                    self.seek_bar.set(percentage)
            except Exception:
                pass
        # Schedule next update
        self.root.after(100, self.update_seek_bar)

    def on_closing(self):
        self.player.stop()
        self.root.destroy()

    def run(self):
        self.update_seek_bar()
        self.root.mainloop()
