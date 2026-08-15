from ctypes import Structure

from core.identity_decoder import identity_decoder
from core.MpvFormat import MpvFormat


class MpvNode(Structure):
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
