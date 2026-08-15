from ctypes import POINTER, Structure, c_char_p, c_int


class MpvEventClientMessage(Structure):
    _fields_ = [("_num_args", c_int), ("_args", POINTER(c_char_p))]

    @property
    def args(self):
        return [self._args[i] for i in range(self._num_args)]
