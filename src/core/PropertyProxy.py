from core.Proxy import Proxy


class PropertyProxy(Proxy):
    def __dir__(self):
        return super().__dir__() + [name.replace("-", "_") for name in self.mpv.property_list]
