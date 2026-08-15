from ctypes import (
    CFUNCTYPE,
    c_char_p,
    c_void_p,
)

MpvGlGetProcAddressFn = CFUNCTYPE(c_void_p, c_void_p, c_char_p)
