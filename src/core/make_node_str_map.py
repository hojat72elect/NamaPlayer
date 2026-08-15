from ctypes import c_char_p, c_void_p, cast, pointer

from core.mpv_coax_proptype import mpv_coax_proptype
from core.MpvFormat import MpvFormat
from core.MpvNodeTypes import MpvNode, MpvNodeList, MpvNodeUnion


def make_node_str_map(d):
    """Take a dict of python objects and make a MPV string node map from it."""
    char_ps = [(c_char_p(k.encode("utf-8")), c_char_p(mpv_coax_proptype(v, str))) for k, v in d.items()]
    node_list = MpvNodeList(num=len(d), keys=(c_char_p * len(d))(*[k for k, v in char_ps]), values=(MpvNode * len(d))(*[MpvNode(format=MpvFormat.STRING, val=MpvNodeUnion(string=v)) for k, v in char_ps]))
    node = MpvNode(format=MpvFormat.NODE_MAP, val=MpvNodeUnion(map=pointer(node_list)))
    return char_ps, node_list, node, cast(pointer(node), c_void_p)
