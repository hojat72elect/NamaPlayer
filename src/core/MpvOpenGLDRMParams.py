from ctypes import Structure, c_int, c_void_p


class MpvOpenGLDRMParams(Structure):
    _fields_ = [("fd", c_int), ("crtc_id", c_int), ("connector_id", c_int), ("atomic_request_ptr", c_void_p), ("render_fd", c_int)]
