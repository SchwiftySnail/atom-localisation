"""Create a simple image with a known centre and add controlled noise."""

import numpy as np


def gaussian_image(shape, centre, sigma, amplitude=1.0, background=0.05):
    """Sample a circular Gaussian at pixel centres; this is not a TEM simulator.

    ``shape`` is (rows, columns); ``centre`` is (x, y), in pixels.
    ``amplitude`` is the height above background of the continuous Gaussian.
    A fractional centre need not land on a pixel, so the sampled maximum can
    be smaller than amplitude + background.
    """
    if len(shape) != 2 or any(not isinstance(n, (int, np.integer)) or n < 3 for n in shape):
        raise ValueError("shape must contain two integer dimensions of at least 3")
    if len(centre) != 2:
        raise ValueError("centre must contain x and y")
    x0, y0 = centre
    if not np.all(np.isfinite([x0, y0, sigma, amplitude, background])):
        raise ValueError("image parameters must be finite")
    if sigma <= 0 or amplitude <= 0 or background < 0:
        raise ValueError("sigma and amplitude must be positive; background must be non-negative")
    if not (0 <= x0 <= shape[1] - 1 and 0 <= y0 <= shape[0] - 1):
        raise ValueError("centre must lie inside the image")

    y, x = np.indices(shape, dtype=float)
    squared_distance = (x - x0) ** 2 + (y - y0) ** 2
    return background + amplitude * np.exp(-squared_distance / (2 * sigma**2))


def add_noise(clean, model, level, rng, amplitude=1.0):
    """Return a new noisy array without changing the clean image.

    Gaussian: level is noise standard deviation as a fraction of amplitude.
    Poisson: level is the expected count at an intensity of one. Counts are
    divided by level afterwards, preserving the clean image's intensity units.
    Gaussian noise is not clipped; Poisson noise is signal-dependent.
    """
    clean = np.asarray(clean, dtype=float)
    if clean.ndim != 2 or not np.all(np.isfinite(clean)):
        raise ValueError("clean must be a finite two-dimensional image")
    if not np.isfinite(level) or not np.isfinite(amplitude) or amplitude <= 0:
        raise ValueError("noise level must be finite and amplitude must be positive")
    if model == "gaussian":
        if level < 0:
            raise ValueError("Gaussian noise level must be non-negative")
        return clean + rng.normal(0, level * amplitude, size=clean.shape)
    if model == "poisson":
        if level <= 0 or np.any(clean < 0):
            raise ValueError("Poisson count scale must be positive and intensities non-negative")
        return rng.poisson(clean * level).astype(float) / level
    raise ValueError(f"Unknown noise model: {model}")
