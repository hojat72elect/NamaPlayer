from ctypes import c_char_p, c_void_p, cast, pointer

from core.mpv_coax_proptype import mpv_coax_proptype
from core.MpvFormat import MpvFormat
from core.MpvNodeTypes import MpvNode, MpvNodeList, MpvNodeUnion


def make_node_str_list(l):
    """Take a list of python objects and make a MPV string node array from it.

    As an example, the python list ``l = [ "foo", 23, false ]`` will result in the following MPV node object::

        struct mpv_node {
            .format = MPV_NODE_ARRAY,
            .u.list = *(struct mpv_node_array){
                .num = len(l),
                .keys = NULL,
                .values = struct mpv_node[len(l)] {
                    { .format = MPV_NODE_STRING, .u.string = l[0] },
                    { .format = MPV_NODE_STRING, .u.string = l[1] },
                    ...
                }
            }
        }
    """
    char_ps = [c_char_p(mpv_coax_proptype(e, str)) for e in l]
    node_list = MpvNodeList(num=len(l), keys=None, values=(MpvNode * len(l))(*[MpvNode(format=MpvFormat.STRING, val=MpvNodeUnion(string=p)) for p in char_ps]))
    node = MpvNode(format=MpvFormat.NODE_ARRAY, val=MpvNodeUnion(list=pointer(node_list)))
    return char_ps, node_list, node, cast(pointer(node), c_void_p)
