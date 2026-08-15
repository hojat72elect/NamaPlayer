from core.MpvFormat import MpvFormat
from core.PropertyProxy import PropertyProxy
from core.py_to_mpv import py_to_mpv


class OSDPropertyProxy(PropertyProxy):
    def __getattr__(self, name):
        return self.mpv._get_property(py_to_mpv(name), fmt=MpvFormat.OSD_STRING)

    def __setattr__(self, _name, _value):
        raise AttributeError("OSD properties are read-only. Please use the regular property API for writing.")
