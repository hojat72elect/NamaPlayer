from core.PropertyProxy import PropertyProxy
from core.py_to_mpv import py_to_mpv


class DecoderPropertyProxy(PropertyProxy):
    def __init__(self, mpv, decoder):
        super().__init__(mpv)
        super().__setattr__("_decoder", decoder)

    def __getattr__(self, name):
        return self.mpv._get_property(py_to_mpv(name), decoder=self._decoder)

    def __setattr__(self, name, value):
        setattr(self.mpv, py_to_mpv(name), value)
