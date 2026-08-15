from ctypes import c_int


class MpvEventID(c_int):
    NONE = 0
    SHUTDOWN = 1
    LOG_MESSAGE = 2
    GET_PROPERTY_REPLY = 3
    SET_PROPERTY_REPLY = 4
    COMMAND_REPLY = 5
    START_FILE = 6
    END_FILE = 7
    FILE_LOADED = 8
    CLIENT_MESSAGE = 16
    VIDEO_RECONFIG = 17
    AUDIO_RECONFIG = 18
    SEEK = 20
    PLAYBACK_RESTART = 21
    PROPERTY_CHANGE = 22
    QUEUE_OVERFLOW = 24
    HOOK = 25

    ANY = (SHUTDOWN, LOG_MESSAGE, GET_PROPERTY_REPLY, SET_PROPERTY_REPLY, COMMAND_REPLY, START_FILE, END_FILE, FILE_LOADED, CLIENT_MESSAGE, VIDEO_RECONFIG, AUDIO_RECONFIG, SEEK, PLAYBACK_RESTART, PROPERTY_CHANGE)

    def __repr__(self):
        return f"<MpvEventID {self.value} {_mpv_event_name(self.value).decode('utf-8')}>"

    @classmethod
    def from_str(kls, s):
        return getattr(kls, s.upper().replace("-", "_"))
