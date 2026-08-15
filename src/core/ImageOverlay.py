import ctypes
from ctypes import addressof, create_string_buffer

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class ImageOverlay:
    def __init__(self, m, overlay_id, img=None, pos=(0, 0)):
        if not PIL_AVAILABLE:
            raise ImportError("PIL/Pillow is required for ImageOverlay. Install it with: pip install Pillow")
        self.m = m
        self.overlay_id = overlay_id
        self.pos = pos
        self._size = None
        if img is not None:
            self.update(img)

    def update(self, img=None, pos=None):
        if img is not None:
            self.img = img
        img = self.img

        w, h = img.size
        stride = w * 4

        if pos is not None:
            self.pos = pos
        x, y = self.pos

        # Pre-multiply alpha channel
        bg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        out = Image.alpha_composite(bg, img)

        # Copy image to ctypes buffer
        if img.size != self._size:
            self._buf = create_string_buffer(w * h * 4)
            self._size = img.size

        ctypes.memmove(self._buf, out.tobytes("raw", "BGRA"), w * h * 4)
        source = "&" + str(addressof(self._buf))

        self.m.overlay_add(self.overlay_id, x, y, source, 0, "bgra", w, h, stride)

    def remove(self):
        self.m.remove_overlay(self.overlay_id)
