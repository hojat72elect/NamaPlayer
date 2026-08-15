from ctypes import POINTER, Structure, c_char, c_char_p, c_size_t, c_void_p, cast


class MpvByteArray(Structure):
    _fields_ = [("data", c_void_p), ("size", c_size_t)]

    def __init__(self, value):
        self._value = value
        self.data = cast(c_char_p(value), c_void_p)
        self.size = len(value)

    def bytes_value(self):
        return cast(self.data, POINTER(c_char))[: self.size]
