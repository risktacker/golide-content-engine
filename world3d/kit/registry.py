"""One registry per layer, so a new world, part or action plugs in with one decorator
and a shot that names something missing fails at once with a list of what exists."""


class Registry:
    def __init__(self, layer):
        self.layer, self.items = layer, {}

    def add(self, name):
        def wrap(fn):
            self.items[name] = fn
            return fn
        return wrap

    def get(self, name):
        if name not in self.items:
            raise KeyError(f"Unknown {self.layer} '{name}'. Available: {sorted(self.items)}")
        return self.items[name]


worlds = Registry("world")
parts = Registry("part builder")
materials = Registry("material")
lights = Registry("light rig")
cameras = Registry("camera move")
actions = Registry("action")
effects = Registry("effect")
