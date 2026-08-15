def lazy_decoder(b):
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b
