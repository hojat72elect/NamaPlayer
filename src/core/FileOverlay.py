class FileOverlay:
    def __init__(self, m, overlay_id, filename=None, size=None, stride=None, pos=(0, 0)):
        self.m = m
        self.overlay_id = overlay_id
        self.pos = pos
        self.size = size
        self.stride = stride
        if filename is not None:
            self.update(filename)

    def update(self, filename=None, size=None, stride=None, pos=None):
        if filename is not None:
            self.filename = filename

        if pos is not None:
            self.pos = pos

        if size is not None:
            self.size = size

        if stride is not None:
            self.stride = stride

        x, y = self.pos
        w, h = self.size
        stride = self.stride or 4 * w

        self.m.overlay_add(self, self.overlay_id, x, y, self.filename, 0, "bgra", w, h, stride)

    def remove(self):
        self.m.remove_overlay(self.overlay_id)
