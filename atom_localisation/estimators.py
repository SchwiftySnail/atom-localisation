"""Four position estimators. None receives the true centre."""

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.optimize import least_squares


METHODS = ("brightest_pixel", "smoothed_peak", "centroid", "gaussian_fit")
LABELS = {
    "brightest_pixel": "Brightest pixel",
    "smoothed_peak": "Smoothed brightest pixel",
    "centroid": "Full-frame clipped centroid",
    "gaussian_fit": "Gaussian fit",
}


@dataclass(frozen=True)
class Estimate:
    x: float | None = None
    y: float | None = None
    failure: str = ""

    @property
    def success(self):
        return self.x is not None and self.y is not None and not self.failure


def _validate_image(image):
    image = np.asarray(image, dtype=float)
    if image.ndim != 2 or min(image.shape) < 3 or not np.all(np.isfinite(image)):
        raise ValueError("image must be a finite 2D array, at least 3 by 3")
    return image


def brightest_pixel(image):
    """Return the brightest pixel's (x, y); ties use NumPy's first occurrence."""
    image = _validate_image(image)
    if np.ptp(image) == 0:
        return Estimate(failure="constant_image")
    row, column = np.unravel_index(np.argmax(image), image.shape)
    return Estimate(float(column), float(row))


def smoothed_peak(image, smoothing_sigma=1.0):
    """Smooth with a fixed Gaussian kernel, then locate a pixel maximum.

    The filter uses reflection at image edges. It does not provide a
    fractional-pixel estimate. Its width is independent of the true spot width.
    """
    image = _validate_image(image)
    if not np.isfinite(smoothing_sigma) or smoothing_sigma <= 0:
        raise ValueError("smoothing_sigma must be positive and finite")
    return brightest_pixel(gaussian_filter(image, smoothing_sigma, mode="reflect"))


def centroid(image, background=0.05):
    """Intensity-weighted centre over the entire image, after clipping.

    This simple baseline is deliberately explicit: it receives the known
    simulated background, subtracts it, and clips negative weights to zero.
    The retained positive noise can pull the estimate towards the frame centre.
    This is not a general implementation of all centroiding methods.
    """
    image = _validate_image(image)
    if not np.isfinite(background):
        raise ValueError("background must be finite")
    if np.ptp(image) == 0:
        return Estimate(failure="constant_image")
    weights = np.maximum(image - background, 0)
    total = weights.sum()
    if total <= 0:
        return Estimate(failure="no_positive_weight")
    y, x = np.indices(image.shape, dtype=float)
    return Estimate(float((weights * x).sum() / total), float((weights * y).sum() / total))


def gaussian_fit(image):
    """Fit amplitude, x, y, width and background with ordinary least squares.

    The true parameters are not passed in. A smoothed image supplies an initial
    peak location; the fit uses the raw image. Ordinary least squares is not a
    Poisson likelihood fit. Failed or boundary-limited fits are reported.
    """
    image = _validate_image(image)
    if np.ptp(image) == 0:
        return Estimate(failure="constant_image")
    y, x = np.indices(image.shape, dtype=float)
    start = smoothed_peak(image)
    background = float(np.median(image))
    amplitude = max(float(image.max()) - background, 1e-6)
    max_sigma = min(image.shape) / 3
    initial = [amplitude, start.x, start.y, min(2.0, max_sigma * 0.8), background]
    lower = [0, 0, 0, 0.3, -np.inf]
    upper = [np.inf, image.shape[1] - 1, image.shape[0] - 1, max_sigma, np.inf]

    def residual(parameters):
        a, x0, y0, sigma, b = parameters
        model = b + a * np.exp(-((x - x0) ** 2 + (y - y0) ** 2) / (2 * sigma**2))
        return (model - image).ravel()

    def jacobian(parameters):
        a, x0, y0, sigma, _ = parameters
        dx, dy = x - x0, y - y0
        exponential = np.exp(-(dx**2 + dy**2) / (2 * sigma**2))
        signal = a * exponential
        return np.column_stack([
            exponential.ravel(),
            (signal * dx / sigma**2).ravel(),
            (signal * dy / sigma**2).ravel(),
            (signal * (dx**2 + dy**2) / sigma**3).ravel(),
            np.ones(image.size),
        ])

    fit = least_squares(
        residual, initial, jac=jacobian, bounds=(lower, upper), max_nfev=150,
        ftol=1e-8, xtol=1e-8, gtol=1e-8,
    )
    if not fit.success or not np.all(np.isfinite(fit.x)):
        return Estimate(failure="fit_did_not_converge")
    if np.any(fit.active_mask):
        return Estimate(failure="fit_at_parameter_bound")
    return Estimate(float(fit.x[1]), float(fit.x[2]))


def estimate_all(image, background=0.05, smoothing_sigma=1.0):
    """Use the same observed image for all four methods."""
    return {
        "brightest_pixel": brightest_pixel(image),
        "smoothed_peak": smoothed_peak(image, smoothing_sigma),
        "centroid": centroid(image, background),
        "gaussian_fit": gaussian_fit(image),
    }
