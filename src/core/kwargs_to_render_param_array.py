from core.MpvRenderParam import MpvRenderParam


def kwargs_to_render_param_array(kwargs):
    t = MpvRenderParam * (len(kwargs) + 1)
    return t(*kwargs.items(), ("invalid", None))
