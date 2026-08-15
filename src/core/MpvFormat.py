from ctypes import c_int


class MpvFormat(c_int):
    NONE = 0
    STRING = 1
    OSD_STRING = 2
    FLAG = 3
    INT64 = 4
    DOUBLE = 5
    NODE = 6
    NODE_ARRAY = 7
    NODE_MAP = 8
    BYTE_ARRAY = 9

    def __eq__(self, other):
        return self is other or self.value == other or self.value == int(other)

    def __repr__(self):
        return ["NONE", "STRING", "OSD_STRING", "FLAG", "INT64", "DOUBLE", "NODE", "NODE_ARRAY", "NODE_MAP", "BYTE_ARRAY"][self.value]

    def __hash__(self):
        return self.value
