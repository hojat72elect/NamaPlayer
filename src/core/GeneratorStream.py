class GeneratorStream:
    """Transform a python generator into a mpv-compatible stream object. The total size of the file can be indicated to
    mpv using the size argument to __init__. Seeking is not supported.
    """

    def __init__(self, generator_fun, size=None):
        self._generator_fun = generator_fun
        self.size = size

    def seek(self, offset):
        self._read_iter = iter(self._generator_fun())
        self._read_chunk = b""
        return 0  # We only support seeking to the first byte atm
        # implementation in case seeking to arbitrary offsets would be necessary
        # while offset > 0:
        #     offset -= len(self.read(offset))
        # return offset

    def read(self, size):
        if not self._read_chunk:
            try:
                self._read_chunk += next(self._read_iter)
            except StopIteration:
                return b""
        rv, self._read_chunk = self._read_chunk[:size], self._read_chunk[size:]
        return rv

    def close(self):
        self._read_iter = iter([])  # make next read() call return EOF

    def cancel(self):
        self._read_iter = iter([])  # make next read() call return EOF
