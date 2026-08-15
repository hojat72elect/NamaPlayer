from core.PropertyProxy import PropertyProxy

_py_to_mpv = lambda name: name.replace("_", "-")


class DecoderPropertyProxy(PropertyProxy):
    def __init__(self, mpv, decoder):
        super().__init__(mpv)
        super().__setattr__("_decoder", decoder)

    def __getattr__(self, name):
        return self.mpv._get_property(_py_to_mpv(name), decoder=self._decoder)

    def __setattr__(self, name, value):
        setattr(self.mpv, _py_to_mpv(name), value)
