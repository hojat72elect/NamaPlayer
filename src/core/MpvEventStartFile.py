from ctypes import Structure, c_ulonglong


class MpvEventStartFile(Structure):
    _fields_ = [
        ("playlist_entry_id", c_ulonglong),
    ]
