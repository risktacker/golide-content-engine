"""Loaded by Python at start-up in the ReachMora kit's processes (its main process and every "spawn" render worker),
because stickman/longform.py puts this folder on PYTHONPATH. When the kit's engine.props module loads, our extra
icons (stickman/rm_extra.py) are added to its ICONS. The kit's own files are never edited (owner 2026-11-17)."""
import importlib.abc
import importlib.util
import sys


class _AddOurIcons(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name != "engine.props":
            return None
        sys.meta_path.remove(self)
        try:
            spec = importlib.util.find_spec(name)
        finally:
            sys.meta_path.insert(0, self)
        if spec is None or spec.loader is None:
            return spec
        run = spec.loader.exec_module

        def exec_module(module):
            run(module)
            from golide_engine.stickman import rm_extra
            rm_extra.register(module)

        spec.loader.exec_module = exec_module
        return spec


sys.meta_path.insert(0, _AddOurIcons())
