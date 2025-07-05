import sys
from typing import Union
import importlib.util
from pathlib import Path
from loguru import logger

def _fqname(py_file: Path) -> str:
    """
    Build a fully-qualified dotted name that matches the real package
    (e.g.  differential.plugins.chdbits) so normal 'import' hits the same
    module object that we create here.
    """
    parts = py_file.with_suffix("").parts
    if "differential" in parts:              # plug-in shipped inside the package
        start = parts.index("differential")
        return ".".join(parts[start:])
    # third-party plug-ins → put them in a unique namespace
    return f"ext_plugins.{py_file.stem}"


def load_plugins_from_dir(directory: Union[str, Path]) -> None:
    """
    Dynamically import all .py files from the given directory,
    so that any classes inheriting from PluginRegister get registered.
    """
    plugin_dir = Path(directory)
    if not plugin_dir.is_dir():
        logger.warning(f"插件目录 '{directory}' 不存在或不是目录。")
        return

    for py_file in plugin_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        _import_module_from_file(py_file)


def load_plugin_from_file(file_path: Union[str, Path]) -> None:
    """
    Dynamically import a single .py file. If it contains a subclass of PluginRegister,
    it will be automatically registered in the global dictionary.
    """
    path_obj = Path(file_path).resolve()
    if not path_obj.is_file():
        logger.warning(f"插件文件 '{file_path}' 不存在或不是文件。")
        return

    _import_module_from_file(path_obj)


def _import_module_from_file(py_file: Path) -> None:
    module_name = _fqname(py_file)

    if module_name in sys.modules:           # already imported → skip
        logger.trace(f"{module_name} already in sys.modules – skipping")
        return

    spec = importlib.util.spec_from_file_location(module_name, py_file)
    module = importlib.util.module_from_spec(spec)

    # Register before executing → later 'import' sees the same object
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    logger.trace(f"Plugin loaded: {module_name}")