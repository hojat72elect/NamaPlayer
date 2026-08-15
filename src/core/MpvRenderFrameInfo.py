from ctypes import Structure, c_int64


class MpvRenderFrameInfo(Structure):
    _fields_ = [("flags", c_int64), ("target_time", c_int64)]

    def as_dict(self):
        return {"flags": self.flags, "target_time": self.target_time}
