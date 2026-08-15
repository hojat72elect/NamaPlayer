from ctypes import Structure, c_int, c_void_p


class MpvOpenGLDRMParamsV2(Structure):
    _fields_ = [("fd", c_int), ("crtc_id", c_int), ("connector_id", c_int), ("atomic_request_ptr", c_void_p), ("render_fd", c_int)]

    def __init__(self, crtc_id, connector_id, atomic_request_ptr, fd=-1, render_fd=-1):
        self.crtc_id, self.connector_id = crtc_id, connector_id
        self.atomic_request_ptr = atomic_request_ptr
        self.fd, self.render_fd = fd, render_fd
