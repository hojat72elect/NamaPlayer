def mpv_coax_proptype(value, proptype=str):
    """Intelligently coax the given python value into something that can be understood as a proptype property."""
    if type(value) is bytes:
        return value
    elif type(value) is bool:
        return b"yes" if value else b"no"
    elif proptype in (str, int, float):
        return str(proptype(value)).encode("utf-8")
    else:
        raise TypeError("Cannot coax value of type {} into property type {}".format(type(value), proptype))
