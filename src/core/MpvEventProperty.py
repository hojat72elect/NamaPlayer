from ctypes import Structure, c_char_p

from core.lazy_decoder import lazy_decoder
from core.MpvFormat import MpvFormat
from core.MpvNodeTypes import MpvNode, MpvNodeUnion


class MpvEventProperty(Structure):
    _fields_ = [("_name", c_char_p), ("format", MpvFormat), ("data", MpvNodeUnion)]

    @property
    def name(self):
        return self._name.decode("utf-8")

    @property
    def value(self):
        return MpvNode.node_cast_value(self.data, self.format.value, decoder=lazy_decoder)
