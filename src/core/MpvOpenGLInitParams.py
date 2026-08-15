from ctypes import Structure, c_void_p

from core.MpvGlGetProcAddressFn import MpvGlGetProcAddressFn


class MpvOpenGLInitParams(Structure):
    _fields_ = [("get_proc_address", MpvGlGetProcAddressFn), ("get_proc_address_ctx", c_void_p), ("extra_exts", c_void_p)]

    def __init__(self, get_proc_address):
        self.get_proc_address = get_proc_address
        self.get_proc_address_ctx = None
        self.extra_exts = None
