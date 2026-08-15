from ctypes import Structure, c_char_p, c_int, c_void_p, cast, pointer

from core.MpvByteArray import MpvByteArray
from core.MpvOpenGLDRMDrawSurfaceSize import MpvOpenGLDRMDrawSurfaceSize
from core.MpvOpenGLDRMParams import MpvOpenGLDRMParams
from core.MpvOpenGLDRMParamsV2 import MpvOpenGLDRMParamsV2
from core.MpvOpenGLFBO import MpvOpenGLFBO
from core.MpvOpenGLInitParams import MpvOpenGLInitParams
from core.MpvRenderFrameInfo import MpvRenderFrameInfo


class MpvRenderParam(Structure):
    _fields_ = [("type_id", c_int), ("data", c_void_p)]

    # maps human-readable type name to (type_id, argtype) tuple.
    # The type IDs come from libmpv/render.h
    TYPES = {
        "invalid": (0, None),
        "api_type": (1, str),
        "opengl_init_params": (2, MpvOpenGLInitParams),
        "opengl_fbo": (3, MpvOpenGLFBO),
        "flip_y": (4, bool),
        "depth": (5, int),
        "icc_profile": (6, bytes),
        "ambient_light": (7, int),
        "x11_display": (8, c_void_p),
        "wl_display": (9, c_void_p),
        "advanced_control": (10, bool),
        "next_frame_info": (11, MpvRenderFrameInfo),
        "block_for_target_time": (12, bool),
        "skip_rendering": (13, bool),
        "drm_display": (14, MpvOpenGLDRMParams),
        "drm_draw_surface_size": (15, MpvOpenGLDRMDrawSurfaceSize),
        "drm_display_v2": (16, MpvOpenGLDRMParamsV2),
    }

    def __init__(self, name, value=None):
        if name not in self.TYPES:
            raise ValueError(f'unknown render param type "{name}"')
        self.type_id, cons = self.TYPES[name]
        if cons is None:
            self.value = None
            self.data = c_void_p()
        elif cons is str:
            self.value = value
            self.data = cast(c_char_p(value.encode("utf-8")), c_void_p)
        elif cons is bytes:
            self.value = MpvByteArray(value)
            self.data = cast(pointer(self.value), c_void_p)
        elif cons is bool:
            self.value = c_int(int(bool(value)))
            self.data = cast(pointer(self.value), c_void_p)
        elif cons is c_void_p:
            self.value = value
            self.data = cast(self.value, c_void_p)
        else:
            self.value = cons(**value)
            self.data = cast(pointer(self.value), c_void_p)
