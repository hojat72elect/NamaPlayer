from ctypes import Structure, c_int


class MpvOpenGLDRMDrawSurfaceSize(Structure):
    _fields_ = [("width", c_int), ("height", c_int)]
