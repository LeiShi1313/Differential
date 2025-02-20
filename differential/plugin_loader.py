import sys
from typing import Union
import importlib.util
from pathlib import Path
from loguru import logger

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
    """
    Helper function to import a Python file via importlib.
    """
    try:
        spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            logger.trace(f"成功导入插件文件: {py_file.name}")
        else:
            logger.warning(f"无法加载插件文件: {py_file}")
    except Exception as e:
        logger.error(f"错误导入插件文件 '{py_file}': {e}")
