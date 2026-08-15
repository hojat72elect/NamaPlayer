from ctypes import POINTER, Union, c_char_p, c_double, c_int, c_int64

from core.MpvByteArray import MpvByteArray
from core.MpvNode import MpvNode
from core.MpvNodeList import MpvNodeList


class MpvNodeUnion(Union):
    _fields_ = [("string", c_char_p), ("flag", c_int), ("int64", c_int64), ("double", c_double), ("node", POINTER(MpvNode)), ("list", POINTER(MpvNodeList)), ("map", POINTER(MpvNodeList)), ("byte_array", POINTER(MpvByteArray))]
