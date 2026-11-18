"""Save labelled figures from the recorded experiment results."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter

from .estimators import LABELS, METHODS, estimate_all
from .model import add_noise, gaussian_image


COLOURS = dict(zip(METHODS, ("#586574", "#d37a22", "#9471a4", "#167d8d")))
MARKERS = dict(zip(METHODS, ("o", "s", "^", "D")))


def save_example(config, output):
    """Use a separate random stream; this example is not part of the trials."""
    centre = config.positions()["fractional"]
    sigma = float(config.sigmas[len(config.sigmas) // 2])
    model = config.noise_models[0]
    levels = config.noise_levels if model == "gaussian" else config.count_scales
    level = float(levels[len(levels) // 2])
    clean = gaussian_image((config.size, config.size), centre, sigma,
                           config.amplitude, config.background)
    rng = np.random.default_rng(np.random.SeedSequence([config.seed, 202]))
    observed = add_noise(clean, model, level, rng, config.amplitude)
    filtered = gaussian_filter(observed, config.smoothing_sigma, mode="reflect")
    estimates = estimate_all(observed, config.background, config.smoothing_sigma)
    figure, axes = plt.subplots(1, 3, figsize=(13, 4.8), layout="constrained")
    low = min(float(observed.min()), float(clean.min()))
    high = max(float(observed.max()), float(clean.max()))
    for axis, image, title in zip(axes, (clean, observed, filtered), (
        "Known clean image", "Noisy image with position estimates", "Gaussian-filtered image"
    )):
        displayed = axis.imshow(image, origin="lower", cmap="gray", interpolation="nearest",
                                vmin=low, vmax=high)
        axis.scatter(*centre, marker="+", s=110, linewidths=2, color="#40becb",
                     label="Known centre", zorder=5)
        axis.set(title=title, xlabel="x (pixels)", ylabel="y (pixels)")
    for method, estimate in estimates.items():
        if estimate.success:
            axes[1].scatter(estimate.x, estimate.y, s=90, facecolors="none",
                            edgecolors=COLOURS[method], marker=MARKERS[method], label=LABELS[method])
    axes[1].legend(fontsize=7, loc="upper left")
    figure.colorbar(displayed, ax=axes, shrink=0.7, label="Intensity (arbitrary units)")
    parameter = "noise SD / amplitude" if model == "gaussian" else "counts per unit intensity"
    figure.suptitle(f"Synthetic spot: {model} noise; {parameter} = {level:g}; spot width = {sigma:g} pixels")
    figure.savefig(output / "example.png", dpi=160)
    plt.close(figure)


def save_error_curves(config, summaries, output):
    paths = []
    positions = list(config.positions())
    for model in config.noise_models:
        figure, axes = plt.subplots(len(positions), len(config.sigmas),
                                    figsize=(4.1 * len(config.sigmas), 9.6),
                                    squeeze=False, layout="constrained")
        for row, position in enumerate(positions):
            for column, sigma in enumerate(config.sigmas):
                axis = axes[row, column]
                for method in METHODS:
                    selected = sorted([
                        item for item in summaries
                        if item["noise_model"] == model and item["position"] == position
                        and item["spot_sigma"] == sigma and item["method"] == method
                    ], key=lambda item: item["noise_level"])
                    x = np.array([item["noise_level"] for item in selected])
                    y = np.array([item["rmse"] if item["rmse"] is not None else np.nan for item in selected])
                    lower = np.array([item["rmse_ci_low"] if item["rmse_ci_low"] is not None else np.nan
                                      for item in selected])
                    upper = np.array([item["rmse_ci_high"] if item["rmse_ci_high"] is not None else np.nan
                                      for item in selected])
                    axis.plot(x, y, "o-", markersize=3, color=COLOURS[method], label=LABELS[method])
                    axis.fill_between(x, lower, upper, alpha=0.12, color=COLOURS[method])
                axis.set_title(f"{position.replace('_', ' ')}; spot width {sigma:g} pixels", fontsize=10)
                axis.set_ylabel("Position RMSE (pixels)")
                if model == "gaussian":
                    axis.set_xlabel("Noise SD / Gaussian amplitude (dimensionless)")
                else:
                    axis.set_xscale("log")
                    axis.set_xlabel("Count scale (counts per unit intensity)")
                axis.set_ylim(bottom=0)
                axis.grid(alpha=0.2)
        axes[0, 0].legend(fontsize=7)
        figure.suptitle(f"{model.capitalize()} noise: position error across {config.trials} trials per condition\n"
                       "Shading: 95% bootstrap interval for RMSE, conditional on successful estimates", fontsize=12)
        name = f"{model}_error_curves.png"
        figure.savefig(output / name, dpi=160)
        plt.close(figure)
        paths.append(name)
    return paths


def reference_scenario(config, rows):
    """Select a recorded scenario for explanation without choosing by performance."""
    model = config.noise_models[0]
    levels = config.noise_levels if model == "gaussian" else config.count_scales
    level = float(levels[len(levels) // 2])
    sigma = float(config.sigmas[len(config.sigmas) // 2])
    return next(row["scenario_id"] for row in rows if row["noise_model"] == model
                and row["noise_level"] == level and row["spot_sigma"] == sigma
                and row["position"] == "off_centre")


def save_error_cloud(config, rows, output):
    scenario = reference_scenario(config, rows)
    selected = [row for row in rows if row["scenario_id"] == scenario and row["success"]]
    extent = max([abs(row[key]) for row in selected for key in ("dx", "dy")] + [0.25]) * 1.1
    figure, axes = plt.subplots(2, 2, figsize=(9, 8), layout="constrained")
    for axis, method in zip(axes.flat, METHODS):
        measured = [row for row in selected if row["method"] == method]
        axis.scatter([row["dx"] for row in measured], [row["dy"] for row in measured],
                     s=12, color=COLOURS[method], alpha=0.5)
        axis.axhline(0, color="black", linewidth=0.6)
        axis.axvline(0, color="black", linewidth=0.6)
        axis.set(xlim=(-extent, extent), ylim=(-extent, extent), aspect="equal",
                 xlabel="Estimated x minus true x (pixels)",
                 ylabel="Estimated y minus true y (pixels)",
                 title=f"{LABELS[method]} ({len(measured)}/{config.trials} successful)")
        axis.grid(alpha=0.15)
    first = next(row for row in rows if row["scenario_id"] == scenario)
    figure.suptitle(f"Position errors for an off-centre spot; identical axis limits\n"
                   f"{first['noise_model']} noise, level {first['noise_level']:g}; "
                   f"width {first['spot_sigma']:g} pixels")
    figure.savefig(output / "error_cloud.png", dpi=160)
    plt.close(figure)
