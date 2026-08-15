def notnull_errcheck(res, func, *args):
    if res is None:
        raise RuntimeError("Underspecified error in MPV when calling {} with args {!r}: NULL pointer returned.Please consult your local debugger.".format(func.__name__, args))
    return res
