from ctypes import POINTER, Structure, Union, c_char_p, c_double, c_int, c_int64

from core.identity_decoder import identity_decoder
from core.MpvByteArray import MpvByteArray
from core.MpvFormat import MpvFormat


class MpvNodeUnion(Union):
    pass


class MpvNodeList(Structure):
    pass


class MpvNode(Structure):
    pass


# Set _fields_ after all classes are defined to handle circular dependencies
MpvNodeUnion._fields_ = [
    ("string", c_char_p),
    ("flag", c_int),
    ("int64", c_int64),
    ("double", c_double),
    ("node", POINTER(MpvNode)),
    ("list", POINTER(MpvNodeList)),
    ("map", POINTER(MpvNodeList)),
    ("byte_array", POINTER(MpvByteArray)),
]

MpvNode._fields_ = [("val", MpvNodeUnion), ("format", MpvFormat)]

MpvNodeList._fields_ = [("num", c_int), ("values", POINTER(MpvNode)), ("keys", POINTER(c_char_p))]


# Add methods to MpvNode
def node_value(self, decoder=identity_decoder):
    return MpvNode.node_cast_value(self.val, self.format.value, decoder)


@staticmethod
def node_cast_value(v, fmt=MpvFormat.NODE, decoder=identity_decoder):
    if fmt == MpvFormat.NONE:
        return None
    elif fmt == MpvFormat.STRING:
        return decoder(v.string)
    elif fmt == MpvFormat.OSD_STRING:
        return v.string.decode("utf-8")
    elif fmt == MpvFormat.FLAG:
        return bool(v.flag)
    elif fmt == MpvFormat.INT64:
        return v.int64
    elif fmt == MpvFormat.DOUBLE:
        return v.double
    else:
        if not v.node:  # Check for null pointer
            return None
        if fmt == MpvFormat.NODE:
            return v.node.contents.node_value(decoder)
        elif fmt == MpvFormat.NODE_ARRAY:
            return v.list.contents.array_value(decoder)
        elif fmt == MpvFormat.NODE_MAP:
            return v.map.contents.dict_value(decoder)
        elif fmt == MpvFormat.BYTE_ARRAY:
            return v.byte_array.contents.bytes_value()
        else:
            raise TypeError("Unknown MPV node format {}. Please submit a bug report.".format(fmt))


MpvNode.node_value = node_value
MpvNode.node_cast_value = node_cast_value


# Add methods to MpvNodeList
def array_value(self, decoder=identity_decoder):
    return [self.values[i].node_value(decoder) for i in range(self.num)]


def dict_value(self, decoder=identity_decoder):
    return {self.keys[i].decode("utf-8"): self.values[i].node_value(decoder) for i in range(self.num)}


MpvNodeList.array_value = array_value
MpvNodeList.dict_value = dict_value
