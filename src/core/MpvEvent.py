from ctypes import POINTER, Structure, c_int, c_ulonglong, c_void_p, cast

from core.MpvEventClientMessage import MpvEventClientMessage
from core.MpvEventCommand import MpvEventCommand
from core.MpvEventEndFile import MpvEventEndFile
from core.MpvEventHook import MpvEventHook
from core.MpvEventID import MpvEventID
from core.MpvEventLogMessage import MpvEventLogMessage
from core.MpvEventProperty import MpvEventProperty
from core.MpvEventStartFile import MpvEventStartFile


class MpvEvent(Structure):
    _fields_ = [("event_id", MpvEventID), ("error", c_int), ("reply_userdata", c_ulonglong), ("_data", c_void_p)]
    _mpv_event_to_node = None
    _mpv_free_node_contents = None

    @property
    def data(self):
        dtype = {
            MpvEventID.GET_PROPERTY_REPLY: MpvEventProperty,
            MpvEventID.PROPERTY_CHANGE: MpvEventProperty,
            MpvEventID.LOG_MESSAGE: MpvEventLogMessage,
            MpvEventID.CLIENT_MESSAGE: MpvEventClientMessage,
            MpvEventID.START_FILE: MpvEventStartFile,
            MpvEventID.END_FILE: MpvEventEndFile,
            MpvEventID.HOOK: MpvEventHook,
            MpvEventID.COMMAND_REPLY: MpvEventCommand,
        }.get(self.event_id.value)
        return cast(self._data, POINTER(dtype)).contents if dtype else None

    def as_dict(self, decoder=None):
        from ctypes import create_string_buffer, pointer, sizeof

        from core.identity_decoder import identity_decoder
        from core.MpvNodeTypes import MpvNode

        if decoder is None:
            decoder = identity_decoder

        out = cast(create_string_buffer(sizeof(MpvNode)), POINTER(MpvNode))
        self._mpv_event_to_node(out, pointer(self))
        rv = out.contents.node_value(decoder=decoder)
        self._mpv_free_node_contents(out)
        return rv

    def __str__(self):
        d = self.data
        return f"<{type(d).__name__} ({self.event_id.value}) err={self.error} p={self.reply_userdata:016x} d={self.as_dict()}>"
