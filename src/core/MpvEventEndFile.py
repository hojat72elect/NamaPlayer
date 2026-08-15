from ctypes import Structure, c_int, c_ulonglong


class MpvEventEndFile(Structure):
    _fields_ = [
        ("reason", c_int),
        ("error", c_int),
        ("playlist_entry_id", c_ulonglong),
        ("playlist_insert_id", c_ulonglong),
        ("playlist_insert_num_entries", c_int),
    ]

    EOF = 0
    RESTARTED = 1
    ABORTED = 2
    QUIT = 3
    ERROR = 4
    REDIRECT = 5
