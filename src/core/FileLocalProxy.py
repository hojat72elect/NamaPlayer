from core.Proxy import Proxy


class FileLocalProxy(Proxy):
    def __getitem__(self, name):
        return self.mpv.__getitem__(name, file_local=True)

    def __setitem__(self, name, value):
        return self.mpv.__setitem__(name, value, file_local=True)

    def __iter__(self):
        return iter(self.mpv)
