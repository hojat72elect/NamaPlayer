from ctypes import CFUNCTYPE, POINTER, Structure, c_char, c_char_p, c_int, c_int64, c_uint64, c_void_p

StreamReadFn = CFUNCTYPE(c_int64, c_void_p, POINTER(c_char), c_uint64)
StreamSeekFn = CFUNCTYPE(c_int64, c_void_p, c_int64)
StreamSizeFn = CFUNCTYPE(c_int64, c_void_p)
StreamCloseFn = CFUNCTYPE(None, c_void_p)
StreamCancelFn = CFUNCTYPE(None, c_void_p)


class StreamCallbackInfo(Structure):
    _fields_ = [("cookie", c_void_p), ("read", StreamReadFn), ("seek", StreamSeekFn), ("size", StreamSizeFn), ("close", StreamCloseFn), ("cancel", StreamCancelFn)]


StreamOpenFn = CFUNCTYPE(c_int, c_void_p, c_char_p, POINTER(StreamCallbackInfo))
