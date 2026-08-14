class Proxy:
    def __init__(self, mpv):
        super().__setattr__("mpv", mpv)
