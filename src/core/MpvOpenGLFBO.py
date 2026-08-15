from ctypes import (
    Structure,
    c_int,
)


class MpvOpenGLFBO(Structure):
    _fields_ = [("fbo", c_int), ("w", c_int), ("h", c_int), ("internal_format", c_int)]

    def __init__(self, w, h, fbo=0, internal_format=0):
        self.w, self.h = w, h
        self.fbo = fbo
        self.internal_format = internal_format
