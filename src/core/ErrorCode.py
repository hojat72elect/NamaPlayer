from core.PropertyUnavailableError import PropertyUnavailableError


class ErrorCode(object):
    """For documentation on these, see mpv's libmpv/client.h."""

    SUCCESS = 0
    EVENT_QUEUE_FULL = -1
    NOMEM = -2
    UNINITIALIZED = -3
    INVALID_PARAMETER = -4
    OPTION_NOT_FOUND = -5
    OPTION_FORMAT = -6
    OPTION_ERROR = -7
    PROPERTY_NOT_FOUND = -8
    PROPERTY_FORMAT = -9
    PROPERTY_UNAVAILABLE = -10
    PROPERTY_ERROR = -11
    COMMAND = -12
    LOADING_FAILED = -13
    AO_INIT_FAILED = -14
    VO_INIT_FAILED = -15
    NOTHING_TO_PLAY = -16
    UNKNOWN_FORMAT = -17
    UNSUPPORTED = -18
    NOT_IMPLEMENTED = -19
    GENERIC = -20

    EXCEPTION_DICT = {
        0: None,
        -1: lambda *a: MemoryError("mpv event queue full", *a),
        -2: lambda *a: MemoryError("mpv cannot allocate memory", *a),
        -3: lambda *a: ValueError("Uninitialized mpv handle used", *a),
        -4: lambda *a: ValueError("Invalid value for mpv parameter", *a),
        -5: lambda *a: AttributeError("mpv option does not exist", *a),
        -6: lambda *a: TypeError("Tried to set mpv option using wrong format", *a),
        -7: lambda *a: ValueError("Invalid value for mpv option", *a),
        -8: lambda *a: AttributeError("mpv property does not exist", *a),
        # Currently (mpv 0.18.1) there is a bug causing a PROPERTY_FORMAT error to be returned instead of
        # INVALID_PARAMETER when setting a property-mapped option to an invalid value.
        -9: lambda *a: TypeError("Tried to get/set mpv property using wrong format, or passed invalid value", *a),
        -10: lambda *a: PropertyUnavailableError("mpv property is not available", *a),
        -11: lambda *a: RuntimeError("Generic error getting or setting mpv property", *a),
        -12: lambda *a: SystemError("Error running mpv command", *a),
        -14: lambda *a: RuntimeError("Initializing the audio output failed", *a),
        -15: lambda *a: RuntimeError("Initializing the video output failed"),
        -16: lambda *a: RuntimeError("There was no audio or video data to play. This also happens if the file was recognized, but did not contain any audio or video streams, or no streams were selected."),
        -17: lambda *a: RuntimeError("When trying to load the file, the file format could not be determined, or the file was too broken to open it"),
        -18: lambda *a: ValueError("Generic error for signaling that certain system requirements are not fulfilled"),
        -19: lambda *a: NotImplementedError("The API function which was called is a stub only"),
        -20: lambda *a: RuntimeError("Unspecified error"),
    }

    @staticmethod
    def human_readable(ec):
        return _mpv_error_string(ec).decode("utf-8")

    @staticmethod
    def default_error_handler(ec, *args):
        return ValueError(ErrorCode.human_readable(ec), ec, *args)

    @classmethod
    def exception_for_ec(kls, ec, *args):
        ec = 0 if ec > 0 else ec
        ex = kls.EXCEPTION_DICT.get(ec, kls.default_error_handler)
        if ex:
            return ex(ec, *args)

    @classmethod
    def raise_for_ec(kls, ec, func, *args):
        ex = kls.exception_for_ec(ec, *args)
        if ex:
            raise ex
