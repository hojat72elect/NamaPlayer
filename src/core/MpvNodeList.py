from ctypes import Structure

from core.identity_decoder import identity_decoder


class MpvNodeList(Structure):
    def array_value(self, decoder=identity_decoder):
        return [self.values[i].node_value(decoder) for i in range(self.num)]

    def dict_value(self, decoder=identity_decoder):
        return {self.keys[i].decode("utf-8"): self.values[i].node_value(decoder) for i in range(self.num)}
