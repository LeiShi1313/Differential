import sys
import inspect
import pkgutil


class Wrapper:
    def __getattr__(self, item):
        return globals().get(item, None)


__all__ = []
for loader, name, is_pkg in pkgutil.walk_packages(__path__):
    spec = loader.find_spec(name)
    if not spec:
        continue
    module = spec.loader.load_module()
    for name, value in inspect.getmembers(module):
        if name.startswith('__'):
            continue
        globals()[name] = value
        # print(name)
        __all__.append(name)
    __all__.append(module)
sys.modules[__name__] = Wrapper()
