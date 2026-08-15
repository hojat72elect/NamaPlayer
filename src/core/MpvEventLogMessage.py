from ctypes import Structure, c_char_p

from core.lazy_decoder import lazy_decoder


class MpvEventLogMessage(Structure):
    _fields_ = [("_prefix", c_char_p), ("_level", c_char_p), ("_text", c_char_p)]

    @property
    def prefix(self):
        return self._prefix.decode("utf-8")

    @property
    def level(self):
        return self._level.decode("utf-8")

    @property
    def text(self):
        return lazy_decoder(self._text)
