from ctypes import Structure

from core.identity_decoder import identity_decoder
from core.MpvNodeTypes import MpvNode


class MpvEventCommand(Structure):
    _fields_ = [("_result", MpvNode)]

    def unpack(self, decoder=identity_decoder):
        return self._result.node_value(decoder=decoder)

    @property
    def result(self):
        return self.unpack()
