"""Motion curves shared by every layer."""


def clamp01(x):
    return min(1.0, max(0.0, x))


def span(t, a, b):
    return clamp01((t - a) / (b - a)) if b > a else float(t >= b)


def smooth(x):
    x = clamp01(x)
    return x * x * x * (x * (6 * x - 15) + 10)
