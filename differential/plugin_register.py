import argparse
from abc import ABCMeta, abstractmethod
from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .base_plugin import Base

REGISTERED_PLUGINS: Dict[str, "Base"] = {}


class PluginRegister(ABCMeta):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        # Skip base class
        if name == "Base":
            return

        aliases = (name.lower(),)
        if "get_aliases" in cls.__dict__:
            aliases += cls.get_aliases()

        from differential.commands import subparsers
        subparser = subparsers.add_parser(name, aliases=aliases, help=cls.get_help())
        subparser.set_defaults(plugin=name)
        cls.add_parser(subparser)

        for alias in aliases:
            REGISTERED_PLUGINS[alias] = cls
        REGISTERED_PLUGINS[name] = cls

    @classmethod
    @abstractmethod
    def get_help(mcs):
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def get_aliases(mcs):
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def add_parser(mcs, parser: argparse.ArgumentParser):
        raise NotImplementedError()
