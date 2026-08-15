from ctypes import c_char_p


def create_null_term_cmd_arg_array(name, args):
    args = [name.encode("utf-8")] + [(arg if type(arg) is bytes else str(arg).encode("utf-8")) for arg in args if arg is not None] + [None]
    return (c_char_p * len(args))(*args)
