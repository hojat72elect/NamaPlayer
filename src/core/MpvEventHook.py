from ctypes import Structure, c_char_p, c_ulonglong


class MpvEventHook(Structure):
    _fields_ = [
        ("_name", c_char_p),
        ("id", c_ulonglong),
    ]

    @property
    def name(self):
        return self._name.decode("utf-8")
