import collections
import ctypes.util
import os.path
import queue
import re
import sys
import threading
import traceback
from concurrent.futures import Future, InvalidStateError
from contextlib import contextmanager
from ctypes import (
    CDLL,
    CFUNCTYPE,
    POINTER,
    c_char_p,
    c_double,
    c_int,
    c_int64,
    c_ulong,
    c_ulonglong,
    c_void_p,
    cast,
    create_string_buffer,
    sizeof,
)
from functools import partial, wraps
from warnings import warn

from core.create_null_term_cmd_arg_array import create_null_term_cmd_arg_array
from core.DecoderPropertyProxy import DecoderPropertyProxy
from core.ErrorCode import ErrorCode
from core.EventOverflowError import EventOverflowError
from core.FileLocalProxy import FileLocalProxy
from core.FileOverlay import FileOverlay
from core.GeneratorStream import GeneratorStream
from core.identity_decoder import identity_decoder
from core.ImageOverlay import ImageOverlay
from core.lazy_decoder import lazy_decoder
from core.make_node_str_list import make_node_str_list
from core.make_node_str_map import make_node_str_map
from core.mpv_coax_proptype import mpv_coax_proptype
from core.MpvEvent import MpvEvent
from core.MpvEventID import MpvEventID
from core.MpvFormat import MpvFormat
from core.MpvHandle import MpvHandle
from core.MpvNodeTypes import MpvNode
from core.MpvRenderContext import MpvRenderContext, RenderUpdateFn
from core.MpvRenderCtxHandle import MpvRenderCtxHandle
from core.MpvRenderParam import MpvRenderParam
from core.notnull_errcheck import notnull_errcheck
from core.OSDPropertyProxy import OSDPropertyProxy
from core.PropertyUnavailableError import PropertyUnavailableError
from core.py_to_mpv import py_to_mpv
from core.ShutdownError import ShutdownError
from core.StreamCallbackInfo import StreamCancelFn, StreamCloseFn, StreamOpenFn, StreamReadFn, StreamSeekFn, StreamSizeFn
from core.strict_decoder import strict_decoder

# We need to first load the dll into our environment.
mpv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib")
if os.path.exists(mpv_path):
    os.add_dll_directory(mpv_path)
    os.environ["PATH"] = mpv_path + os.pathsep + os.environ.get("PATH", "")

if os.name == "nt":
    # we're in Windows OS
    names = ["libmpv-2.dll"]
    for name in names:
        dll = ctypes.util.find_library(name)
        if dll:
            break
    else:
        for name in names:
            dll = os.path.join(os.path.dirname(__file__), name)
            if os.path.isfile(dll):
                break
        else:
            raise OSError('Cannot find libmpv-2.dll in your system %PATH%. One way to deal with this is to ship the dll with your script and put the directory your script is in into %PATH% before "import mpv": os.environ["PATH"] = os.path.dirname(__file__) + os.pathsep + os.environ["PATH"] If mpv-1.dll is located elsewhere, you can add that path to os.environ["PATH"].')

    try:
        # flags argument: LOAD_LIBRARY_SEARCH_DEFAULT_DIRS | LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR
        # cf. https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-loadlibraryexa
        backend = CDLL(dll, 0x00001000 | 0x00000100)
    except Exception as e:
        if not os.path.isabs(dll):  # can only be find_library, not the "look next to mpv.py" thing
            raise OSError(
                f'ctypes.find_library found mpv.dll at {dll}, but ctypes.CDLL could not load it. It looks like find_library found mpv.dll under a relative path entry in %PATH%. Please make sure all paths in %PATH% are absolute. Instead of trying to load mpv.dll from the current working directory, put it somewhere next to your script and add that path to %PATH% using os.environ["PATH"] = os.path.dirname(__file__) + os.pathsep + os.environ["PATH"]'
            ) from e
        else:
            raise OSError(f"ctypes.find_library found mpv.dll at {dll}, but ctypes.CDLL could not load it.") from e
    fs_enc = "utf-8"

else:
    import locale

    lc, enc = locale.getlocale(locale.LC_NUMERIC)
    # libmpv requires LC_NUMERIC to be set to "C". Since messing with global variables everyone else relies upon is
    # still better than segfaulting, we are setting LC_NUMERIC to "C".
    locale.setlocale(locale.LC_NUMERIC, "C")

    sofile = ctypes.util.find_library("mpv")
    if sofile is None:
        raise OSError("Cannot find libmpv in the usual places. Depending on your distro, you may try installing an mpv-devel or mpv-libs package. If you have libmpv around but this script can't find it, consult the documentation for ctypes.util.find_library which this script uses to look up the library filename.")
    backend = CDLL(sofile)
    fs_enc = sys.getfilesystemencoding()


WakeupCallback = CFUNCTYPE(None, c_void_p)


def _handle_func(name, args, restype, errcheck, ctx=MpvHandle, deprecated=False):
    func = getattr(backend, name)
    func.argtypes = [ctx] + args if ctx else args
    if restype is not None:
        func.restype = restype
    if errcheck is not None:
        func.errcheck = errcheck
    if deprecated:

        @wraps(func)
        def wrapper(*args, **kwargs):
            if not wrapper.warned:  # Only warn on first invocation to prevent spamming
                warn("Backend C api has been deprecated: " + name, DeprecationWarning, stacklevel=2)
                wrapper.warned = True
            return func(*args, **kwargs)

        wrapper.warned = False

        globals()["_" + name] = wrapper
    else:
        globals()["_" + name] = func


def bytes_free_errcheck(res, func, *args):
    notnull_errcheck(res, func, *args)
    rv = cast(res, c_void_p).value
    _mpv_free(res)
    return rv


ec_errcheck = ErrorCode.raise_for_ec

backend.mpv_client_api_version.restype = c_ulong


def _mpv_client_api_version():
    ver = backend.mpv_client_api_version()
    return ver >> 16, ver & 0xFFFF


MPV_VERSION = _mpv_client_api_version()
if MPV_VERSION < (1, 108):
    ver = ".".join(str(num) for num in MPV_VERSION)
    raise RuntimeError(f"python-mpv requires libmpv with an API version of 1.108 or higher (libmpv >= 0.33), but you have an older version ({ver}).")

backend.mpv_free.argtypes = [c_void_p]
_mpv_free = backend.mpv_free

backend.mpv_free_node_contents.argtypes = [c_void_p]
_mpv_free_node_contents = backend.mpv_free_node_contents

backend.mpv_create.restype = MpvHandle
_mpv_create = backend.mpv_create

_handle_func("mpv_create_client", [c_char_p], MpvHandle, notnull_errcheck)
_handle_func("mpv_create_weak_client", [c_char_p], MpvHandle, notnull_errcheck)
_handle_func("mpv_client_name", [], c_char_p, errcheck=None)
_handle_func("mpv_initialize", [], c_int, ec_errcheck)
_handle_func("mpv_destroy", [], None, errcheck=None)
_handle_func("mpv_terminate_destroy", [], None, errcheck=None)
_handle_func("mpv_load_config_file", [c_char_p], c_int, ec_errcheck)
_handle_func("mpv_get_time_us", [], c_ulonglong, errcheck=None)

_handle_func("mpv_set_option", [c_char_p, MpvFormat, c_void_p], c_int, ec_errcheck)
_handle_func("mpv_set_option_string", [c_char_p, c_char_p], c_int, ec_errcheck)

_handle_func("mpv_command", [POINTER(c_char_p)], c_int, ec_errcheck)
_handle_func("mpv_command_string", [c_char_p, c_char_p], c_int, ec_errcheck)
_handle_func("mpv_command_async", [c_ulonglong, POINTER(c_char_p)], c_int, ec_errcheck)
_handle_func("mpv_command_node", [POINTER(MpvNode), POINTER(MpvNode)], c_int, ec_errcheck)
_handle_func("mpv_command_node_async", [c_ulonglong, POINTER(MpvNode)], c_int, ec_errcheck)
_handle_func("mpv_abort_async_command", [c_ulonglong], None, errcheck=None)

_handle_func("mpv_set_property", [c_char_p, MpvFormat, c_void_p], c_int, ec_errcheck)
_handle_func("mpv_set_property_string", [c_char_p, c_char_p], c_int, ec_errcheck)
_handle_func("mpv_set_property_async", [c_ulonglong, c_char_p, MpvFormat, c_void_p], c_int, ec_errcheck)
_handle_func("mpv_get_property", [c_char_p, MpvFormat, c_void_p], c_int, ec_errcheck)
_handle_func("mpv_get_property_string", [c_char_p], c_void_p, bytes_free_errcheck)
_handle_func("mpv_get_property_osd_string", [c_char_p], c_void_p, bytes_free_errcheck)
_handle_func("mpv_get_property_async", [c_ulonglong, c_char_p, MpvFormat], c_int, ec_errcheck)
_handle_func("mpv_observe_property", [c_ulonglong, c_char_p, MpvFormat], c_int, ec_errcheck)
_handle_func("mpv_unobserve_property", [c_ulonglong], c_int, ec_errcheck)

_handle_func("mpv_event_name", [c_int], c_char_p, errcheck=None, ctx=None)
_handle_func("mpv_event_to_node", [POINTER(MpvNode), POINTER(MpvEvent)], c_int, ec_errcheck, ctx=None)
_handle_func("mpv_error_string", [c_int], c_char_p, errcheck=None, ctx=None)

_handle_func("mpv_request_event", [MpvEventID, c_int], c_int, ec_errcheck)
_handle_func("mpv_request_log_messages", [c_char_p], c_int, ec_errcheck)
_handle_func("mpv_wait_event", [c_double], POINTER(MpvEvent), errcheck=None)
_handle_func("mpv_wakeup", [], None, errcheck=None)
_handle_func("mpv_set_wakeup_callback", [WakeupCallback, c_void_p], None, errcheck=None)

_handle_func("mpv_stream_cb_add_ro", [c_char_p, c_void_p, StreamOpenFn], c_int, ec_errcheck)

_handle_func("mpv_render_context_create", [MpvRenderCtxHandle, MpvHandle, POINTER(MpvRenderParam)], c_int, ec_errcheck, ctx=None)
_handle_func("mpv_render_context_set_parameter", [MpvRenderParam], c_int, ec_errcheck, ctx=MpvRenderCtxHandle)
_handle_func("mpv_render_context_get_info", [MpvRenderParam], c_int, ec_errcheck, ctx=MpvRenderCtxHandle)
_handle_func("mpv_render_context_set_update_callback", [RenderUpdateFn, c_void_p], None, errcheck=None, ctx=MpvRenderCtxHandle)
_handle_func("mpv_render_context_update", [], c_int64, errcheck=None, ctx=MpvRenderCtxHandle)
_handle_func("mpv_render_context_render", [POINTER(MpvRenderParam)], c_int, ec_errcheck, ctx=MpvRenderCtxHandle)
_handle_func("mpv_render_context_report_swap", [], None, errcheck=None, ctx=MpvRenderCtxHandle)
_handle_func("mpv_render_context_free", [], None, errcheck=None, ctx=MpvRenderCtxHandle)

# Set up MpvEvent with the functions it needs
MpvEvent._mpv_event_to_node = _mpv_event_to_node
MpvEvent._mpv_free_node_contents = _mpv_free_node_contents

# Set up MpvRenderContext with the functions it needs
MpvRenderContext._mpv_render_context_create = _mpv_render_context_create
MpvRenderContext._mpv_render_context_set_parameter = _mpv_render_context_set_parameter
MpvRenderContext._mpv_render_context_get_info = _mpv_render_context_get_info
MpvRenderContext._mpv_render_context_set_update_callback = _mpv_render_context_set_update_callback
MpvRenderContext._mpv_render_context_update = _mpv_render_context_update
MpvRenderContext._mpv_render_context_render = _mpv_render_context_render
MpvRenderContext._mpv_render_context_report_swap = _mpv_render_context_report_swap
MpvRenderContext._mpv_render_context_free = _mpv_render_context_free


def _event_generator(handle):
    while True:
        event = _mpv_wait_event(handle, -1).contents
        if event.event_id.value == MpvEventID.NONE:
            raise StopIteration()
        yield event


_mpv_to_py = lambda name: name.replace("-", "_")

_drop_nones = lambda *args: [arg for arg in args if arg is not None]


class MPV(object):
    """See man mpv(1) for the details of the implemented commands. All mpv properties can be accessed as
    ``my_mpv.some_property`` and all mpv options can be accessed as ``my_mpv['some-option']``.

    By default, properties are returned as decoded ``str`` and an error is thrown if the value does not contain valid
    utf-8. To get a decoded ``str`` if possibly but ``bytes`` instead of an error if not, use
    ``my_mpv.lazy.some_property``. To always get raw ``bytes``, use ``my_mpv.raw.some_property``.  To access a
    property's decoded OSD value, use ``my_mpv.osd.some_property``.

    To get API information on an option, use ``my_mpv.option_info('option-name')``. To get API information on a
    property, use ``my_mpv.properties['property-name']``. Take care to use mpv's dashed-names instead of the
    underscore_names exposed on the python object.

    To make your program not barf hard the first time its used on a weird file system **always** access properties
    containing file names or file tags through ``MPV.raw``."""

    def __init__(self, *extra_mpv_flags, log_handler=None, start_event_thread=True, loglevel=None, **extra_mpv_opts):
        """Create an MPV instance.

        Extra arguments and extra keyword arguments will be passed to mpv as options.
        """

        self.handle = _mpv_create()
        self._event_thread = None
        self._core_shutdown = False

        _mpv_set_option_string(self.handle, b"audio-display", b"no")
        istr = lambda o: ("yes" if o else "no") if type(o) is bool else str(o)
        try:
            for flag in extra_mpv_flags:
                _mpv_set_option_string(self.handle, flag.encode("utf-8"), b"")
            for k, v in extra_mpv_opts.items():
                _mpv_set_option_string(self.handle, k.replace("_", "-").encode("utf-8"), istr(v).encode("utf-8"))
        finally:
            _mpv_initialize(self.handle)

        self.osd = OSDPropertyProxy(self)
        self.file_local = FileLocalProxy(self)
        self.raw = DecoderPropertyProxy(self, identity_decoder)
        self.strict = DecoderPropertyProxy(self, strict_decoder)
        self.lazy = DecoderPropertyProxy(self, lazy_decoder)

        self._event_callbacks = []
        self._command_reply_callbacks = {}
        self._event_handler_lock = threading.Lock()
        self._property_handlers = collections.defaultdict(lambda: [])
        self._quit_handlers = set()
        self._message_handlers = {}
        self._key_binding_handlers = {}
        self._event_handle = _mpv_create_client(self.handle, b"py_event_handler")
        self._log_handler = log_handler
        self._stream_protocol_cbs = {}
        self._stream_protocol_frontends = collections.defaultdict(lambda: {})
        self.register_stream_protocol("python", self._python_stream_open)
        self._python_streams = {}
        self._python_stream_catchall = None
        self._exception_futures = set()
        self.overlay_ids = set()
        self.overlays = {}
        if loglevel is not None or log_handler is not None:
            self.set_loglevel(loglevel or "terminal-default")
        if start_event_thread:
            self._event_thread = threading.Thread(target=self._loop, name="MPVEventHandlerThread")
            self._event_thread.daemon = True
            self._event_thread.start()
        else:
            self._event_thread = None
        if m := re.search(r"(\d+)\.(\d+)\.(\d+)", self.mpv_version):
            self.mpv_version_tuple = tuple(map(int, m.groups()))

    @contextmanager
    def _enqueue_exceptions(self):
        try:
            yield
        except Exception as e:
            for fut in self._exception_futures:
                try:
                    fut.set_exception(e)
                    break
                except InvalidStateError:
                    pass
            else:
                warn(f"Unhandled exception on python-mpv event loop: {e}\n{traceback.format_exc()}", RuntimeWarning)

    def _loop(self):
        for event in _event_generator(self._event_handle):
            try:
                eid = event.event_id.value

                with self._event_handler_lock:
                    if eid == MpvEventID.SHUTDOWN:
                        self._core_shutdown = True

                for callback in self._event_callbacks:
                    with self._enqueue_exceptions():
                        callback(event)

                if eid == MpvEventID.PROPERTY_CHANGE:
                    pc = event.data
                    name, value, _fmt = pc.name, pc.value, pc.format
                    for handler in self._property_handlers[name]:
                        with self._enqueue_exceptions():
                            handler(name, value)

                if eid == MpvEventID.LOG_MESSAGE and self._log_handler is not None:
                    ev = event.data
                    with self._enqueue_exceptions():
                        self._log_handler(ev.level, ev.prefix, ev.text)

                if eid == MpvEventID.CLIENT_MESSAGE:
                    # {'event': {'args': ['key-binding', 'foo', 'u-', 'g']}, 'reply_userdata': 0, 'error': 0, 'event_id': 16}
                    target, *args = event.data.args
                    target = target.decode("utf-8")
                    if target in self._message_handlers:
                        with self._enqueue_exceptions():
                            self._message_handlers[target](*args)

                if eid == MpvEventID.COMMAND_REPLY:
                    key = event.reply_userdata
                    callback = self._command_reply_callbacks.pop(key, None)
                    if callback:
                        with self._enqueue_exceptions():
                            callback(ErrorCode.exception_for_ec(event.error), event.data)

                if eid == MpvEventID.QUEUE_OVERFLOW:
                    # cache list, since error handlers will unregister themselves
                    for cb in list(self._command_reply_callbacks.values()):
                        with self._enqueue_exceptions():
                            cb(EventOverflowError("libmpv event queue has flown over because events have not been processed fast enough"), None)

                if eid == MpvEventID.SHUTDOWN:
                    _mpv_destroy(self._event_handle)
                    for cb in list(self._command_reply_callbacks.values()):
                        with self._enqueue_exceptions():
                            cb(ShutdownError("libmpv core has been shutdown"), None)
                    return

            except Exception as e:
                warn(f"Unhandled {e} inside python-mpv event loop!\n{traceback.format_exc()}", RuntimeWarning)

    @property
    def core_shutdown(self):
        """Property indicating whether the core has been shut down. Possible causes for this are e.g. the `quit` command
        or a user closing the mpv window."""
        return self._core_shutdown

    def check_core_alive(self):
        """This method can be used as a sanity check to tests whether the core is still alive at the time it is
        called."""
        if self._core_shutdown:
            raise ShutdownError("libmpv core has been shutdown")

    def wait_until_paused(self, timeout=None, catch_errors=True):
        """Waits until playback of the current title is paused or done. Raises a ShutdownError if the core is shutdown while
        waiting."""
        self.wait_for_property("core-idle", timeout=timeout, catch_errors=catch_errors)

    def wait_for_playback(self, timeout=None, catch_errors=True):
        """Waits until playback of the current title is finished. Raises a ShutdownError if the core is shutdown while
        waiting.
        """
        self.wait_for_event("end_file", timeout=timeout, catch_errors=catch_errors)

    def wait_until_playing(self, timeout=None, catch_errors=True):
        """Waits until playback of the current title has started. Raises a ShutdownError if the core is shutdown while
        waiting."""
        self.wait_for_property("core-idle", lambda idle: not idle, timeout=timeout, catch_errors=catch_errors)

    def wait_for_property(self, name, cond=lambda val: val, level_sensitive=True, timeout=None, catch_errors=True):
        """Waits until ``cond`` evaluates to a truthy value on the named property. This can be used to wait for
        properties such as ``idle_active`` indicating the player is done with regular playback and just idling around.
        Raises a ShutdownError when the core is shutdown while waiting.
        """
        with self.prepare_and_wait_for_property(name, cond, level_sensitive, timeout=timeout, catch_errors=catch_errors) as result:
            pass
        return result.result()

    def wait_for_shutdown(self, timeout=None, catch_errors=True):
        """Wait for core to shutdown (e.g. through quit() or terminate())."""
        try:
            self.wait_for_event(None, timeout=timeout, catch_errors=catch_errors)
        except ShutdownError:
            return

    def _set_error_handler(self, future):
        @self.event_callback("shutdown", "queue-overflow")
        def shutdown_handler(event):
            nonlocal future
            try:
                if event.event_id.value == MpvEventID.SHUTDOWN:
                    future.set_exception(ShutdownError("libmpv core has been shutdown"))
                else:
                    future.set_exception(EventOverflowError("libmpv event queue has flown over because events have not been processed fast enough"))
            except InvalidStateError:
                pass

        return shutdown_handler.unregister_mpv_events

    @contextmanager
    def prepare_and_wait_for_property(self, name, cond=lambda val: val, level_sensitive=True, timeout=None, catch_errors=True):
        """Context manager that waits until ``cond`` evaluates to a truthy value on the named property. See
        prepare_and_wait_for_event for usage.
        Raises a ShutdownError when the core is shutdown while waiting. Re-raises any errors inside ``cond``.
        """
        result = Future()

        def observer(name, val):
            try:
                rv = cond(val)
                if rv:
                    result.set_result(rv)

            except InvalidStateError:
                pass

            except Exception as e:
                try:
                    result.set_exception(e)
                except:
                    pass

        try:
            result.set_running_or_notify_cancel()

            self.observe_property(name, observer)
            err_unregister = self._set_error_handler(result)
            if catch_errors:
                self._exception_futures.add(result)

            yield result

            if level_sensitive:
                rv = cond(getattr(self, name.replace("-", "_")))
                if rv:
                    result.set_result(rv)
                    return

            self.check_core_alive()
            result.result(timeout)

        except InvalidStateError:
            pass

        finally:
            err_unregister()
            self.unobserve_property(name, observer)
            self._exception_futures.discard(result)

    def wait_for_event(self, *event_types, cond=lambda evt: True, timeout=None, catch_errors=True):
        """Waits for the indicated event(s). If cond is given, waits until cond(event) is true. Raises a ShutdownError
        if the core is shutdown while waiting. This also happens when 'shutdown' is in event_types. Re-raises any error
        inside ``cond``.
        """
        with self.prepare_and_wait_for_event(*event_types, cond=cond, timeout=timeout, catch_errors=catch_errors) as result:
            pass
        return result.result()

    @contextmanager
    def prepare_and_wait_for_event(self, *event_types, cond=lambda evt: True, timeout=None, catch_errors=True):
        """Context manager that waits for the indicated event(s) like wait_for_event after running. If cond is given,
        waits until cond(event) is true. Raises a ShutdownError if the core is shutdown while waiting. This also happens
        when 'shutdown' is in event_types. Re-raises any error inside ``cond``.

        Compared to wait_for_event this handles the case where a thread waits for an event it itself causes in a
        thread-safe way. An example from the testsuite is:

        with self.m.prepare_and_wait_for_event('client_message'):
            self.m.keypress(key)

        Using just wait_for_event it would be impossible to ensure the event is caught since it may already have been
        handled in the interval between keypress(...) running and a subsequent wait_for_event(...) call.
        """
        result = Future()

        @self.event_callback(*event_types)
        def target_handler(evt):
            try:
                rv = cond(evt)
                if rv:
                    result.set_result(rv)
            except Exception as e:
                try:
                    result.set_exception(e)
                except InvalidStateError:
                    pass
            except InvalidStateError:
                pass

        err_unregister = self._set_error_handler(result)

        try:
            result.set_running_or_notify_cancel()
            if catch_errors:
                self._exception_futures.add(result)

            yield result

            self.check_core_alive()
            result.result(timeout)

        finally:
            err_unregister()
            target_handler.unregister_mpv_events()
            self._exception_futures.discard(result)

    def __del__(self):
        if self.handle:
            self.terminate()

    def terminate(self):
        """Properly terminates this player instance. Preferably use this instead of relying on python's garbage
        collector to cause this to be called from the object's destructor.

        This method will detach the main libmpv handle and wait for mpv to shut down and the event thread to finish.
        """
        self.handle, handle = None, self.handle
        if threading.current_thread() is self._event_thread:
            raise UserWarning("terminate() should not be called from event thread (e.g. from a callback function). If you want to terminate mpv from here, please call quit() instead, then sync the main thread against the event thread using e.g. wait_for_shutdown(), then terminate() from the main thread. This call has been transformed into a call to quit().")
            self.quit()
        else:
            _mpv_terminate_destroy(handle)
            if self._event_thread:
                self._event_thread.join()

    def set_loglevel(self, level):
        """Set MPV's log level. This adjusts which output will be sent to this object's log handlers. If you just want
        mpv's regular terminal output, you don't need to adjust this but just need to pass a log handler to the MPV
        constructur such as ``MPV(log_handler=print)``.

        Valid log levels are "no", "fatal", "error", "warn", "info", "v" "debug" and "trace". For details see your mpv's
        client.h header file.
        """
        _mpv_request_log_messages(self._event_handle, level.encode("utf-8"))

    def string_command(self, name, *args):
        """Execute a raw command."""
        args = create_null_term_cmd_arg_array(name, args)
        _mpv_command(self.handle, args)

    def command_async(self, name, *args, callback=None, decoder=lazy_decoder, **kwargs):
        """Same as mpv_command, but run the command asynchronously. If you provide a callback, that callback will be
        called after completion or on error. This method returns a future that evaluates to the result of the callback
        (if given), and the result of the libmpv call otherwise.

        Usage example:

            future = player.command_async(...)
            try:
                print('The result was', future.result())
            except Exception as e:
                print('mpv returned an error:', e)
        """

        future = Future()
        future.set_running_or_notify_cancel()

        if callback is None:

            def callback(error, result):
                if error:
                    raise error
                return result

        def wrapper(error, result):
            try:
                result = result.unpack(decoder)
                future.set_result(callback(error, result))
            except Exception as e:
                try:
                    future.set_exception(e)
                except InvalidStateError:
                    pass

        def abort():
            _mpv_abort_async_command(self._event_handle, id(future))
            del self._command_reply_callbacks[id(future)]

        future.cancel = abort

        self._command_reply_callbacks[id(future)] = wrapper

        if kwargs:
            if args:
                raise ValueError("Can only call mpv commands either using positional or using named arguments, not a mix of both.")
            kwargs["name"] = name
            _1, _2, _3, pointer = make_node_str_map(kwargs)
        else:
            _1, _2, _3, pointer = make_node_str_list([name, *args])

        ppointer = cast(pointer, POINTER(MpvNode))
        _mpv_command_node_async(self._event_handle, id(future), ppointer)
        return future

    def node_command(self, name, *args, decoder=strict_decoder):
        self.command(name, *args, decoder=decoder)

    def command(self, name, *args, decoder=strict_decoder, **kwargs):
        if kwargs:
            if args:
                raise ValueError("Can only call mpv commands either using positional or using named arguments, not a mix of both.")
            kwargs["name"] = name
            _1, _2, _3, pointer = make_node_str_map(kwargs)
        else:
            _1, _2, _3, pointer = make_node_str_list([name, *args])

        out = cast(create_string_buffer(sizeof(MpvNode)), POINTER(MpvNode))
        ppointer = cast(pointer, POINTER(MpvNode))
        _mpv_command_node(self.handle, ppointer, out)
        rv = out.contents.node_value(decoder=decoder)
        _mpv_free_node_contents(out)
        return rv

    def seek(self, amount, reference="relative", precision="keyframes"):
        """Mapped mpv seek command, see man mpv(1)."""
        self.command("seek", amount, reference, precision)

    def revert_seek(self):
        """Mapped mpv revert_seek command, see man mpv(1)."""
        self.command("revert_seek")

    def frame_step(self):
        """Mapped mpv frame-step command, see man mpv(1)."""
        self.command("frame-step")

    def frame_back_step(self):
        """Mapped mpv frame_back_step command, see man mpv(1)."""
        self.command("frame_back_step")

    def property_add(self, name, value=1):
        """Add the given value to the property's value. On overflow or underflow, clamp the property to the maximum. If
        ``value`` is omitted, assume ``1``.
        """
        self.command("add", name, value)

    def property_multiply(self, name, factor):
        """Multiply the value of a property with a numeric factor."""
        self.command("multiply", name, factor)

    def cycle(self, name, direction="up"):
        """Cycle the given property. ``up`` and ``down`` set the cycle direction. On overflow, set the property back to
        the minimum, on underflow set it to the maximum. If ``up`` or ``down`` is omitted, assume ``up``.
        """
        self.command("cycle", name, direction)

    def screenshot(self, includes="subtitles", mode="single"):
        """Mapped mpv screenshot command, see man mpv(1)."""
        self.command("screenshot", includes, mode)

    def screenshot_to_file(self, filename, includes="subtitles"):
        """Mapped mpv screenshot_to_file command, see man mpv(1)."""
        self.command("screenshot_to_file", filename.encode(fs_enc), includes)

    def screenshot_raw(self, includes="subtitles"):
        """Mapped mpv screenshot_raw command, see man mpv(1). Returns a pillow Image object."""
        from PIL import Image

        res = self.command("screenshot-raw", includes)
        if res["format"] != "bgr0":
            raise ValueError('Screenshot in unknown format "{}". Currently, only bgr0 is supported.'.format(res["format"]))
        img = Image.frombytes("RGBA", (res["stride"] // 4, res["h"]), res["data"])
        b, g, r, a = img.split()
        return Image.merge("RGB", (r, g, b))

    def allocate_overlay_id(self):
        free_ids = set(range(64)) - self.overlay_ids
        if not free_ids:
            raise IndexError("All overlay IDs are in use")
        next_id, *_ = sorted(free_ids)
        self.overlay_ids.add(next_id)
        return next_id

    def free_overlay_id(self, overlay_id):
        self.overlay_ids.remove(overlay_id)

    def create_file_overlay(self, filename=None, size=None, stride=None, pos=(0, 0)):
        overlay_id = self.allocate_overlay_id()
        overlay = FileOverlay(self, overlay_id, filename, size, stride, pos)
        self.overlays[overlay_id] = overlay
        return overlay

    def create_image_overlay(self, img=None, pos=(0, 0)):
        overlay_id = self.allocate_overlay_id()
        overlay = ImageOverlay(self, overlay_id, img, pos)
        self.overlays[overlay_id] = overlay
        return overlay

    def remove_overlay(self, overlay_id):
        self.overlay_remove(overlay_id)
        self.free_overlay_id(overlay_id)
        del self.overlays[overlay_id]

    def playlist_next(self, mode="weak"):
        """Mapped mpv playlist_next command, see man mpv(1)."""
        self.command("playlist_next", mode)

    def playlist_prev(self, mode="weak"):
        """Mapped mpv playlist_prev command, see man mpv(1)."""
        self.command("playlist_prev", mode)

    def playlist_play_index(self, idx):
        """Mapped mpv playlist-play-index command, see man mpv(1)."""
        self.command("playlist-play-index", idx)

    @staticmethod
    def _encode_options(options):
        return ",".join("{}={}".format(py_to_mpv(str(key)), str(val)) for key, val in options.items())

    def loadfile(self, filename, mode="replace", index=None, **options):
        """Mapped mpv loadfile command, see man mpv(1)."""
        if self.mpv_version_tuple >= (0, 38, 0):
            if index is None:
                index = -1
            self.command("loadfile", filename.encode(fs_enc), mode, index, MPV._encode_options(options))
        else:
            if index is not None:
                warn(f"The index argument to the loadfile command is only supported on mpv >= 0.38.0")
            self.command("loadfile", filename.encode(fs_enc), mode, MPV._encode_options(options))

    def loadlist(self, playlist, mode="replace"):
        """Mapped mpv loadlist command, see man mpv(1)."""
        self.command("loadlist", playlist.encode(fs_enc), mode)

    def playlist_clear(self):
        """Mapped mpv playlist_clear command, see man mpv(1)."""
        self.command("playlist_clear")

    def playlist_remove(self, index="current"):
        """Mapped mpv playlist_remove command, see man mpv(1)."""
        self.command("playlist_remove", index)

    def playlist_move(self, index1, index2):
        """Mapped mpv playlist_move command, see man mpv(1)."""
        self.command("playlist_move", index1, index2)

    def playlist_shuffle(self):
        """Mapped mpv playlist-shuffle command, see man mpv(1)."""
        self.command("playlist-shuffle")

    def playlist_unshuffle(self):
        """Mapped mpv playlist-unshuffle command, see man mpv(1)."""
        self.command("playlist-unshuffle")

    def run(self, command, *args):
        """Mapped mpv run command, see man mpv(1)."""
        self.command("run", command, *args)

    def quit(self, code=None):
        """Mapped mpv quit command, see man mpv(1)."""
        if code is not None:
            self.command("quit", code)
        else:
            self.command("quit")

    def quit_watch_later(self, code=None):
        """Mapped mpv quit_watch_later command, see man mpv(1)."""
        if code is not None:
            self.command("quit_watch_later", code)
        else:
            self.command("quit_watch_later")

    def stop(self, keep_playlist=False):
        """Mapped mpv stop command, see man mpv(1)."""
        if keep_playlist:
            self.command("stop", "keep-playlist")
        else:
            self.command("stop")

    def audio_add(self, url, flags="select", title=None, lang=None):
        """Mapped mpv audio_add command, see man mpv(1)."""
        self.command("audio_add", url.encode(fs_enc), *_drop_nones(flags, title, lang))

    def audio_remove(self, audio_id=None):
        """Mapped mpv audio_remove command, see man mpv(1)."""
        self.command("audio_remove", audio_id)

    def audio_reload(self, audio_id=None):
        """Mapped mpv audio_reload command, see man mpv(1)."""
        self.command("audio_reload", audio_id)

    def video_add(self, url, flags="select", title=None, lang=None, albumart=None):
        """Mapped mpv video_add command, see man mpv(1)."""
        self.command("video_add", url.encode(fs_enc), *_drop_nones(flags, title, lang, albumart))

    def video_remove(self, video_id=None):
        """Mapped mpv video_remove command, see man mpv(1)."""
        self.command("video_remove", video_id)

    def video_reload(self, video_id=None):
        """Mapped mpv video_reload command, see man mpv(1)."""
        self.command("video_reload", video_id)

    def sub_add(self, url, flags="select", title=None, lang=None):
        """Mapped mpv sub_add command, see man mpv(1)."""
        self.command("sub_add", url.encode(fs_enc), *_drop_nones(flags, title, lang))

    def sub_remove(self, sub_id=None):
        """Mapped mpv sub_remove command, see man mpv(1)."""
        self.command("sub_remove", sub_id)

    def sub_reload(self, sub_id=None):
        """Mapped mpv sub_reload command, see man mpv(1)."""
        self.command("sub_reload", sub_id)

    def sub_step(self, skip):
        """Mapped mpv sub_step command, see man mpv(1)."""
        self.command("sub_step", skip)

    def sub_seek(self, skip):
        """Mapped mpv sub_seek command, see man mpv(1)."""
        self.command("sub_seek", skip)

    def toggle_osd(self):
        """Mapped mpv osd command, see man mpv(1)."""
        self.command("osd")

    def print_text(self, text):
        """Mapped mpv print-text command, see man mpv(1)."""
        self.command("print-text", text)

    def show_text(self, string, duration="-1", level=0):
        """Mapped mpv show_text command, see man mpv(1)."""
        self.command("show_text", string, duration, level)

    def expand_text(self, text):
        """Mapped mpv expand-text command, see man mpv(1)."""
        return self.command("expand-text", text)

    def expand_path(self, path):
        """Mapped mpv expand-path command, see man mpv(1)."""
        return self.command("expand-path", path)

    def show_progress(self):
        """Mapped mpv show_progress command, see man mpv(1)."""
        self.command("show_progress")

    def rescan_external_files(self, mode="reselect"):
        """Mapped mpv rescan-external-files command, see man mpv(1)."""
        self.command("rescan-external-files", mode)

    def discnav(self, command):
        """Mapped mpv discnav command, see man mpv(1)."""
        self.command("discnav", command)

    def mouse(self, x, y, button=None, mode="single"):
        """Mapped mpv mouse command, see man mpv(1)."""
        if button is None:
            self.command("mouse", x, y, mode)
        else:
            self.command("mouse", x, y, button, mode)

    def keypress(self, name):
        """Mapped mpv keypress command, see man mpv(1)."""
        self.command("keypress", name)

    def keydown(self, name):
        """Mapped mpv keydown command, see man mpv(1)."""
        self.command("keydown", name)

    def keyup(self, name=None):
        """Mapped mpv keyup command, see man mpv(1)."""
        if name is None:
            self.command("keyup")
        else:
            self.command("keyup", name)

    def keybind(self, name, command):
        """Mapped mpv keybind command, see man mpv(1)."""
        self.command("keybind", name, command)

    def write_watch_later_config(self):
        """Mapped mpv write_watch_later_config command, see man mpv(1)."""
        self.command("write_watch_later_config")

    def overlay_add(self, overlay_id, x, y, file_or_fd, offset, fmt, w, h, stride):
        """Mapped mpv overlay_add command, see man mpv(1)."""
        self.command("overlay_add", overlay_id, x, y, file_or_fd, offset, fmt, w, h, stride)

    def overlay_remove(self, overlay_id):
        """Mapped mpv overlay_remove command, see man mpv(1)."""
        self.command("overlay_remove", overlay_id)

    def osd_overlay(self, overlay_id, data, res_x=0, res_y=720, z=0, hidden=False):
        self.command("osd_overlay", id=overlay_id, data=data, res_x=res_x, res_y=res_y, z=z, hidden=hidden, format="ass-events")

    def osd_overlay_remove(self, overlay_id):
        self.command("osd_overlay", id=overlay_id, format="none")

    def script_message(self, *args):
        """Mapped mpv script_message command, see man mpv(1)."""
        self.command("script_message", *args)

    def script_message_to(self, target, *args):
        """Mapped mpv script_message_to command, see man mpv(1)."""
        self.command("script_message_to", target, *args)

    def drop_buffers(self):
        self.command("drop_buffers")

    def vf_command(self, label, command, argument):
        self.command("vf_command", label, command, argument)

    def af_command(self, label, command, argument):
        self.command("af_command", label, command, argument)

    def observe_property(self, name, handler):
        """Register an observer on the named property. An observer is a function that is called with the new property
        value every time the property's value is changed. The basic function signature is ``fun(property_name,
        new_value)`` with new_value being the decoded property value as a python object. This function can be used as a
        function decorator if no handler is given.

        To unregister the observer, call either of ``mpv.unobserve_property(name, handler)``,
        ``mpv.unobserve_all_properties(handler)`` or the handler's ``unobserve_mpv_properties`` attribute::

            @player.property_observer('volume')
            def my_handler(property_name, new_volume):
                print("It's loud!", new_volume)

            my_handler.unobserve_mpv_properties()

        exit_handler is a function taking no arguments that is called when the underlying mpv handle is terminated (e.g.
        from calling MPV.terminate() or issuing a "quit" input command).
        """
        self._property_handlers[name].append(handler)
        _mpv_observe_property(self._event_handle, hash(name) & 0xFFFFFFFFFFFFFFFF, name.encode("utf-8"), MpvFormat.NODE)

    def property_observer(self, name):
        """Function decorator to register a property observer. See ``MPV.observe_property`` for details."""

        def wrapper(fun):
            self.observe_property(name, fun)
            fun.unobserve_mpv_properties = lambda: self.unobserve_property(name, fun)
            return fun

        return wrapper

    def unobserve_property(self, name, handler):
        """Unregister a property observer. This requires both the observed property's name and the handler function that
        was originally registered as one handler could be registered for several properties. To unregister a handler
        from *all* observed properties see ``unobserve_all_properties``.
        """
        self._property_handlers[name].remove(handler)
        if not self._property_handlers[name]:
            _mpv_unobserve_property(self._event_handle, hash(name) & 0xFFFFFFFFFFFFFFFF)

    def unobserve_all_properties(self, handler):
        """Unregister a property observer from *all* observed properties."""
        for name in self._property_handlers:
            self.unobserve_property(name, handler)

    def register_message_handler(self, target, handler=None):
        """Register a mpv script message handler. This can be used to communicate with embedded lua scripts. Pass the
        script message target name this handler should be listening to and the handler function.

        WARNING: Only one handler can be registered at a time for any given target.

        To unregister the message handler, call its ``unregister_mpv_messages`` function::

            player = mpv.MPV()
            @player.message_handler('foo')
            def my_handler(some, args):
                print(args)

            my_handler.unregister_mpv_messages()
        """
        self._register_message_handler_internal(target, handler)

    def _register_message_handler_internal(self, target, handler):
        self._message_handlers[target] = handler

    def unregister_message_handler(self, target_or_handler):
        """Unregister a mpv script message handler for the given script message target name.

        You can also call the ``unregister_mpv_messages`` function attribute set on the handler function when it is
        registered.
        """
        if isinstance(target_or_handler, str):
            del self._message_handlers[target_or_handler]
        else:
            for key, val in self._message_handlers.items():
                if val == target_or_handler:
                    del self._message_handlers[key]

    def message_handler(self, target):
        """Decorator to register a mpv script message handler.

        WARNING: Only one handler can be registered at a time for any given target.

        To unregister the message handler, call its ``unregister_mpv_messages`` function::

            player = mpv.MPV()
            @player.message_handler('foo')
            def my_handler(some, args):
                print(args)

            my_handler.unregister_mpv_messages()
        """

        def register(handler):
            self._register_message_handler_internal(target, handler)
            handler.unregister_mpv_messages = lambda: self.unregister_message_handler(handler)
            return handler

        return register

    def register_event_callback(self, callback):
        """Register a blanket event callback receiving all event types.

        To unregister the event callback, call its ``unregister_mpv_events`` function::

            player = mpv.MPV()
            @player.event_callback('shutdown')
            def my_handler(event):
                print('It ded.')

            my_handler.unregister_mpv_events()
        """
        self._event_callbacks.append(callback)

    def unregister_event_callback(self, callback):
        """Unregiser an event callback."""
        self._event_callbacks.remove(callback)

    def event_callback(self, *event_types):
        """Function decorator to register a blanket event callback for the given event types. Event types can be given
        as str (e.g.  'start-file'), integer or MpvEventID object.

        WARNING: Due to the way this is filtering events, this decorator cannot be chained with itself.

        To unregister the event callback, call its ``unregister_mpv_events`` function::

            player = mpv.MPV()
            @player.event_callback('shutdown')
            def my_handler(event):
                print('It ded.')

            my_handler.unregister_mpv_events()
        """

        def register(callback):
            with self._event_handler_lock:
                self.check_core_alive()
                types = [MpvEventID.from_str(t) if isinstance(t, str) else t for t in event_types] or MpvEventID.ANY

                @wraps(callback)
                def wrapper(event, *args, **kwargs):
                    if event.event_id.value in types:
                        callback(event, *args, **kwargs)

                self._event_callbacks.append(wrapper)
                wrapper.unregister_mpv_events = partial(self.unregister_event_callback, wrapper)
                return wrapper

        return register

    @staticmethod
    def _binding_name(callback_or_cmd):
        return "py_kb_{:016x}".format(hash(callback_or_cmd) & 0xFFFFFFFFFFFFFFFF)

    def on_key_press(self, keydef, mode="force", repetition=False):
        """Function decorator to register a simplified key binding. The callback is called whenever the key given is
        *pressed*. When the ``repetition=True`` is passed, the callback is called again repeatedly while the key is held
        down.

        To unregister the callback function, you can call its ``unregister_mpv_key_bindings`` attribute::

            player = mpv.MPV()
            @player.on_key_press('Q')
            def binding():
                print('blep')

            binding.unregister_mpv_key_bindings()

        WARNING: For a single keydef only a single callback/command can be registered at the same time. If you register
        a binding multiple times older bindings will be overwritten and there is a possibility of references leaking. So
        don't do that.

        The BIG FAT WARNING regarding untrusted keydefs from the key_binding method applies here as well.
        """

        def register(fun):
            @self.key_binding(keydef, mode)
            @wraps(fun)
            def wrapper(state="p-", name=None, char=None, *_):
                if state[0] in ("d", "p") or (repetition and state[0] == "r"):
                    fun()

            return wrapper

        return register

    def key_binding(self, keydef, mode="force"):
        """Function decorator to register a low-level key binding.

        The callback function signature is ``fun(key_state, key_name, key_char, scale, arg)``.

        The key_state contains up to three chars, corresponding to the regex ``[udr]([m-][c-]?)?``. ``[udr]`` means
        "key up", "key down", or "repetition" for when the key is held down. "m" indicates mouse events, and "c"
        indicates key up events resulting from a logical cancellation. For details check out the mpv man page.

        The keydef format is: ``[Shift+][Ctrl+][Alt+][Meta+]<key>`` where ``<key>`` is either the literal character the
        key produces (ASCII or Unicode character), or a symbolic name (as printed by ``mpv --input-keylist``).

        To unregister the callback function, you can call its ``unregister_mpv_key_bindings`` attribute::

            player = mpv.MPV()
            @player.key_binding('Q')
            def binding(state, name, char):
                print('blep')

            binding.unregister_mpv_key_bindings()

        WARNING: For a single keydef only a single callback/command can be registered at the same time. If you register
        a binding multiple times older bindings will be overwritten and there is a possibility of references leaking. So
        don't do that.

        BIG FAT WARNING: mpv's key binding mechanism is pretty powerful.  This means, you essentially get arbitrary code
        exectution through key bindings. This interface makes some limited effort to sanitize the keydef given in the
        first parameter, but YOU SHOULD NOT RELY ON THIS IN FOR SECURITY. If your input comes from config files, this is
        completely fine--but, if you are about to pass untrusted input into this parameter, better double-check whether
        this is secure in your case.
        """

        def register(fun):
            fun.mpv_key_bindings = getattr(fun, "mpv_key_bindings", []) + [keydef]

            def unregister_all():
                for keydef in fun.mpv_key_bindings:
                    self.unregister_key_binding(keydef)

            fun.unregister_mpv_key_bindings = unregister_all

            self.register_key_binding(keydef, fun, mode)
            return fun

        return register

    def register_key_binding(self, keydef, callback_or_cmd, mode="force"):
        """Register a key binding. This takes an mpv keydef and either a string containing a mpv command or a python
        callback function.  See ``MPV.key_binding`` for details.
        """
        if not re.match(r"(Shift+)?(Ctrl+)?(Alt+)?(Meta+)?(.|\w+)", keydef):
            raise ValueError("Invalid keydef. Expected format: [Shift+][Ctrl+][Alt+][Meta+]<key>\n<key> is either the literal character the key produces (ASCII or Unicode character), or a symbolic name (as printed by --input-keylist")
        binding_name = MPV._binding_name(keydef)
        if callable(callback_or_cmd):
            self._key_binding_handlers[binding_name] = callback_or_cmd
            self.register_message_handler("key-binding", self._handle_key_binding_message)
            self.command("define-section", binding_name, "{} script-binding py_event_handler/{}".format(keydef, binding_name), mode)
        elif isinstance(callback_or_cmd, str):
            self.command("define-section", binding_name, "{} {}".format(keydef, callback_or_cmd), mode)
        else:
            raise TypeError("register_key_binding expects either an str with an mpv command or a python callable.")
        self.command("enable-section", binding_name, "allow-hide-cursor+allow-vo-dragging")

    def _handle_key_binding_message(self, binding_name, key_state, key_name=None, key_char=None, scale=None, arg=None, *_):
        binding_name = binding_name.decode("utf-8")
        key_state = key_state.decode("utf-8")
        key_name = key_name.decode("utf-8") if key_name is not None else None
        key_char = key_char.decode("utf-8") if key_char is not None else None
        self._key_binding_handlers[binding_name](key_state, key_name, key_char, scale, arg)

    def unregister_key_binding(self, keydef):
        """Unregister a key binding by keydef."""
        binding_name = MPV._binding_name(keydef)
        self.command("disable-section", binding_name)
        self.command("define-section", binding_name, "")
        if binding_name in self._key_binding_handlers:
            del self._key_binding_handlers[binding_name]
            if not self._key_binding_handlers:
                self.unregister_message_handler("key-binding")

    def register_stream_protocol(self, proto, open_fn=None):
        """Register a custom stream protocol as documented in libmpv/stream_cb.h:
        https://github.com/mpv-player/mpv/blob/master/libmpv/stream_cb.h

        proto is the protocol scheme, e.g. "foo" for "foo://" urls.

        This function can either be used with two parameters or it can be used as a decorator on the target
        function.

        open_fn is a function taking an URI string and returning an mpv stream object.
        open_fn may raise a ValueError to signal libmpv the URI could not be opened.

        The mpv stream protocol is as follows:
        class Stream:
            @property
            def size(self):
                return None # unknown size
                return size # int with size in bytes

            def read(self, size):
                ...
                return read # non-empty bytes object with input
                return b'' # empty byte object signals permanent EOF

            def seek(self, pos): # optional
                return new_offset # integer with new byte offset. The new offset may be before the requested offset
                in case an exact seek is inconvenient.

            def close(self): # optional
                ...

            def cancel(self): # optional
                Abort a running read() or seek() operation
                ...

        """

        def decorator(open_fn):
            @StreamOpenFn
            def open_backend(_userdata, uri, cb_info):
                try:
                    frontend = open_fn(uri.decode("utf-8"))
                except ValueError:
                    return ErrorCode.LOADING_FAILED
                except Exception as e:
                    for fut in self._exception_futures:
                        try:
                            fut.set_exception(e)
                            break
                        except InvalidStateError:
                            pass
                    else:
                        warnings.warn(f"Unhandled exception {e} inside stream open callback for URI {uri}\n{traceback.format_exc()}")
                    return ErrorCode.LOADING_FAILED

                cb_info.contents.cookie = None

                def read_backend(_userdata, buf, bufsize):
                    with self._enqueue_exceptions():
                        data = frontend.read(bufsize)
                        for i in range(len(data)):
                            buf[i] = data[i]
                        return len(data)
                    return -1

                read = cb_info.contents.read = StreamReadFn(read_backend)

                def close_backend(_userdata):
                    with self._enqueue_exceptions():
                        del self._stream_protocol_frontends[proto][uri]
                        if hasattr(frontend, "close"):
                            frontend.close()

                close = cb_info.contents.close = StreamCloseFn(close_backend)

                seek, size, cancel = None, None, None

                if hasattr(frontend, "seek"):

                    def seek_backend(_userdata, offx):
                        with self._enqueue_exceptions():
                            return frontend.seek(offx)
                        return ErrorCode.GENERIC

                    seek = cb_info.contents.seek = StreamSeekFn(seek_backend)

                if hasattr(frontend, "size") and frontend.size is not None:

                    def size_backend(_userdata):
                        with self._enqueue_exceptions():
                            return frontend.size
                        return 0

                    size = cb_info.contents.size = StreamSizeFn(size_backend)

                if hasattr(frontend, "cancel"):

                    def cancel_backend(_userdata):
                        with self._enqueue_exceptions():
                            frontend.cancel()

                    cancel = cb_info.contents.cancel = StreamCancelFn(cancel_backend)

                # keep frontend and callbacks in memory until closed
                frontend._registered_callbacks = [read, close, seek, size, cancel]
                self._stream_protocol_frontends[proto][uri] = frontend
                return 0

            if proto in self._stream_protocol_cbs:
                raise KeyError("Stream protocol already registered")
            # keep backend in memory forever
            self._stream_protocol_cbs[proto] = [open_backend]
            _mpv_stream_cb_add_ro(self.handle, proto.encode("utf-8"), c_void_p(), open_backend)

            return open_fn

        if open_fn is not None:
            decorator(open_fn)
        return decorator

    # Convenience functions
    def play(self, filename):
        """Play a path or URL (requires ``ytdl`` option to be set)."""
        self.loadfile(filename)

    @property
    def playlist_filenames(self):
        """Return all playlist item file names/URLs as a list of strs."""
        return [element["filename"] for element in self.playlist]

    def playlist_append(self, filename, **options):
        """Append a path or URL to the playlist. This does not start playing the file automatically. To do that, use
        ``MPV.loadfile(filename, 'append-play')``."""
        self.loadfile(filename, "append", **options)

    # "Python stream" logic. This is some porcelain for directly playing data from python generators.

    def _python_stream_open(self, uri):
        """Internal handler for python:// protocol streams registered through @python_stream(...) and
        @python_stream_catchall
        """
        (name,) = re.fullmatch("python://(.*)", uri).groups()

        if name in self._python_streams:
            generator_fun, size = self._python_streams[name]
        else:
            if self._python_stream_catchall is not None:
                generator_fun, size = self._python_stream_catchall(name)
            else:
                raise ValueError("Python stream name not found and no catch-all defined")

        return GeneratorStream(generator_fun, size)

    def python_stream(self, name=None, size=None):
        """Register a generator for the python stream with the given name.

        name is the name, i.e. the part after the "python://" in the URI, that this generator is registered as.
        size is the total number of bytes in the stream (if known).

        Any given name can only be registered once. The catch-all can also only be registered once. To unregister a
        stream, call the .unregister function set on the callback.

        If name is None (the default), a name and corresponding python:// URI are automatically generated. You can
        access the name through the .stream_name property set on the callback, and the stream URI for passing into
        mpv.play(...) through the .stream_uri property.

        The generator signals EOF by returning, manually raising StopIteration or by yielding b'', an empty bytes
        object.

        The generator may be called multiple times if libmpv seeks or loops.

        See also: @mpv.python_stream_catchall

        @mpv.python_stream('foobar')
        def reader():
            for chunk in chunks:
                yield chunk
        mpv.play('python://foobar')
        mpv.wait_for_playback()
        reader.unregister()
        """

        def register(cb):
            nonlocal name
            if name is None:
                name = f"__python_mpv_anonymous_python_stream_{id(cb)}__"

            if name in self._python_streams:
                raise KeyError('Python stream name "{}" is already registered'.format(name))

            self._python_streams[name] = (cb, size)

            def unregister():
                if name not in self._python_streams or self._python_streams[name][0] is not cb:  # This is just a basic sanity check
                    raise RuntimeError("Python stream has already been unregistered")
                del self._python_streams[name]

            cb.unregister = unregister
            cb.stream_name = name
            cb.stream_uri = f"python://{name}"
            return cb

        return register

    @contextmanager
    def play_context(self):
        """Context manager for streaming bytes straight into libmpv.

        This is a convenience wrapper around python_stream. play_context returns a write method, which you can use in
        the body of the context manager to feed libmpv bytes. All bytes you feed in with write() in the body of a single
        call of this context manager are treated as one single file. A queue is used internally, so this function is
        thread-safe. The queue is unlimited, so it cannot block and is safe to call from async code. You can use this
        function to stream chunked data, e.g. from the network.

        Use it like this:

        with m.play_context() as write:
            with open(TESTVID, 'rb') as f:
                while (chunk := f.read(65536)): # Get some chunks of bytes
                    write(chunk)
        """
        q = queue.Queue()

        EOF = object()  # Get some unique object as EOF marker

        @self.python_stream()
        def reader():
            while (chunk := q.get()) is not EOF:
                if chunk:
                    yield chunk
            reader.unregister()

        def write(chunk):
            q.put(chunk)

        # Start playback before yielding, the first call to reader() will block until write is called at least once.
        self.play(reader.stream_uri)
        yield write
        q.put(EOF)

    def play_bytes(self, data):
        """Play the given bytes object as a single file."""

        @self.python_stream()
        def reader():
            yield data
            reader.unregister()  # unregister itself

        self.play(reader.stream_uri)

    def python_stream_catchall(self, cb):
        """Register a catch-all python stream to be called when no name matches can be found. Use this decorator on a
        function that takes a name argument and returns a (generator, size) tuple (with size being None if unknown).

        An invalid URI can be signalled to libmpv by raising a ValueError inside the callback.

        See also: @mpv.python_stream(name, size)

        @mpv.python_stream_catchall
        def catchall(name):
            if not name.startswith('foo'):
                raise ValueError('Unknown Name')

            def foo_reader():
                with open(name, 'rb') as f:
                    while True:
                        chunk = f.read(1024)
                        if not chunk:
                            break
                        yield chunk
            return foo_reader, None
        mpv.play('python://foo23')
        mpv.wait_for_playback()
        catchall.unregister()
        """
        if self._python_stream_catchall is not None:
            raise KeyError("A catch-all python stream is already registered")

        self._python_stream_catchall = cb

        def unregister():
            if self._python_stream_catchall is not cb:
                raise RuntimeError("This catch-all python stream has already been unregistered")
            self._python_stream_catchall = None

        cb.unregister = unregister
        return cb

    # Property accessors
    def _get_property(self, name, decoder=strict_decoder, fmt=MpvFormat.NODE):
        self.check_core_alive()
        out = create_string_buffer(sizeof(MpvNode))
        try:
            cval = _mpv_get_property(self.handle, name.encode("utf-8"), fmt, out)

            if fmt is MpvFormat.OSD_STRING:
                return cast(out, POINTER(c_char_p)).contents.value.decode("utf-8")
            elif fmt is MpvFormat.NODE:
                rv = cast(out, POINTER(MpvNode)).contents.node_value(decoder=decoder)
                _mpv_free_node_contents(out)
                return rv
            else:
                raise TypeError("_get_property only supports NODE and OSD_STRING formats.")
        except PropertyUnavailableError as ex:
            return None

    def _set_property(self, name, value):
        self.check_core_alive()
        ename = name.encode("utf-8")
        if isinstance(value, dict):
            _1, _2, _3, pointer = make_node_str_map(value)
            _mpv_set_property(self.handle, ename, MpvFormat.NODE, pointer)
        elif isinstance(value, (list, set)):
            _1, _2, _3, pointer = make_node_str_list(value)
            _mpv_set_property(self.handle, ename, MpvFormat.NODE, pointer)
        else:
            _mpv_set_property_string(self.handle, ename, mpv_coax_proptype(value))

    def __getattr__(self, name):
        return self._get_property(py_to_mpv(name), lazy_decoder)

    def __setattr__(self, name, value):
        try:
            if name != "handle" and not name.startswith("_"):
                self._set_property(py_to_mpv(name), value)
            else:
                super().__setattr__(name, value)
        except AttributeError:
            super().__setattr__(name, value)

    def __dir__(self):
        return super().__dir__() + [name.replace("-", "_") for name in self.property_list]

    @property
    def properties(self):
        return {name: self.option_info(name) for name in self.property_list}

    # Dict-like option access
    def __getitem__(self, name, file_local=False):
        """Get an option value."""
        prefix = "file-local-options/" if file_local else "options/"
        return self._get_property(prefix + name, lazy_decoder)

    def __setitem__(self, name, value, file_local=False):
        """Set an option value."""
        prefix = "file-local-options/" if file_local else "options/"
        return self._set_property(prefix + name, value)

    def __iter__(self):
        """Iterate over all option names."""
        return iter(self.options)

    def option_info(self, name):
        """Get information on the given option."""
        try:
            return self._get_property("option-info/" + name)
        except AttributeError:
            return None
