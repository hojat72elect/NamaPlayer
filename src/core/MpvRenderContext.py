from ctypes import CFUNCTYPE, POINTER, c_void_p, cast, create_string_buffer, sizeof

from core.kwargs_to_render_param_array import kwargs_to_render_param_array
from core.MpvRenderCtxHandle import MpvRenderCtxHandle
from core.MpvRenderParam import MpvRenderParam

RenderUpdateFn = CFUNCTYPE(None, c_void_p)


class MpvRenderContext:
    _mpv_render_context_create = None
    _mpv_render_context_set_parameter = None
    _mpv_render_context_get_info = None
    _mpv_render_context_set_update_callback = None
    _mpv_render_context_update = None
    _mpv_render_context_render = None
    _mpv_render_context_report_swap = None
    _mpv_render_context_free = None

    def __init__(self, mpv, api_type, **kwargs):
        self._mpv = mpv
        kwargs["api_type"] = api_type

        buf = cast(create_string_buffer(sizeof(MpvRenderCtxHandle)), POINTER(MpvRenderCtxHandle))
        self._mpv_render_context_create(buf, mpv.handle, kwargs_to_render_param_array(kwargs))
        self._handle = buf.contents

    def free(self):
        self._mpv_render_context_free(self._handle)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)

        elif name == "update_cb":
            func = value if value else (lambda: None)
            self._update_cb = value
            self._update_fn_wrapper = RenderUpdateFn(lambda _userdata: func())
            self._mpv_render_context_set_update_callback(self._handle, self._update_fn_wrapper, None)

        else:
            param = MpvRenderParam(name, value)
            self._mpv_render_context_set_parameter(self._handle, param)

    def __getattr__(self, name):
        if name == "update_cb":
            return self._update_cb

        elif name == "handle":
            return self._handle

        param = MpvRenderParam(name)
        data_type = type(param.data.contents)
        buf = cast(create_string_buffer(sizeof(data_type)), POINTER(data_type))
        param.data = buf
        self._mpv_render_context_get_info(self._handle, param)
        return buf.contents.as_dict()

    def update(self):
        """Calls mpv_render_context_update and returns the MPV_RENDER_UPDATE_FRAME flag (see render.h)"""
        return bool(self._mpv_render_context_update(self._handle) & 1)

    def render(self, **kwargs):
        self._mpv_render_context_render(self._handle, kwargs_to_render_param_array(kwargs))

    def report_swap(self):
        self._mpv_render_context_report_swap(self._handle)
