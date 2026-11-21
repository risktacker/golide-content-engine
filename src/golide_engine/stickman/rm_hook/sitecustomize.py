"""Loaded by Python at start-up in the ReachMora kit's processes (its main process and every "spawn" render worker),
because stickman/longform.py puts this folder on PYTHONPATH. When the kit's engine.props module loads, our extra
icons (rm_extra), places (rm_sets) and moving pictures/camera moves (rm_moves) are added. The kit's own files are never edited (owner 2026-11-17)."""
import importlib.abc
import importlib.util
import sys


OURS = {"engine.props": "rm_extra", "engine.sets": "rm_sets", "engine.shots": "rm_moves"}   # kit module -> our add-on


class _AddOurIcons(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name not in OURS:
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
            ours = importlib.import_module("golide_engine.stickman." + OURS[name])
            ours.register(module)

        spec.loader.exec_module = exec_module
        return spec


sys.meta_path.insert(0, _AddOurIcons())
