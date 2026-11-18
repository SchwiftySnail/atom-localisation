"""Write inspectable data, environment information and a short results report."""

import csv
from datetime import datetime, timezone
import json
import platform
from pathlib import Path
import subprocess

import matplotlib
import numpy as np
import scipy

from . import __version__
from .estimators import LABELS
from .plots import reference_scenario


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def metadata(config):
    repository = Path(__file__).resolve().parents[1]

    def git(*arguments):
        try:
            return subprocess.check_output(["git", *arguments], cwd=repository,
                                           stderr=subprocess.DEVNULL, text=True).strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    status = git("status", "--porcelain")
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "project_version": __version__, "python": platform.python_version(),
        "numpy": np.__version__, "scipy": scipy.__version__, "matplotlib": matplotlib.__version__,
        "platform": platform.platform(), "git_commit": git("rev-parse", "HEAD"),
        "git_branch": git("branch", "--show-current"),
        "git_dirty": bool(status) if status is not None else None,
        "configuration": config.to_dict(),
        "randomness": "SeedSequence(seed).spawn(scenarios); shared noisy frame across methods. "
                      "Separate streams [seed, 101] for bootstrap and [seed, 202] for example.",
        "note": "Seeded results are reproducible in the recorded environment; numerical and random "
                "implementations can change across dependency versions.",
    }


def write_outputs(config, rows, summaries, output, curve_paths):
    write_csv(output / "trials.csv", rows)
    write_csv(output / "summary.csv", summaries)
    (output / "summary.json").write_text(json.dumps(summaries, indent=2, allow_nan=False) + "\n")
    (output / "metadata.json").write_text(json.dumps(metadata(config), indent=2, allow_nan=False) + "\n")
    scenario = reference_scenario(config, rows)
    selected = [item for item in summaries if item["scenario_id"] == scenario]
    first = selected[0]
    lines = [
        "# Synthetic atom localisation: results", "",
        "These results come from a simplified single-Gaussian image model. "
        "They do not establish accuracy on experimental electron microscopy images.", "",
        f"The experiment generated {len(rows) // 4:,} noisy images and {len(rows):,} method results. "
        f"Each condition used {config.trials} trials with root random seed {config.seed}.", "",
        "## What the images show", "", "![Clean, noisy and filtered example](example.png)", "",
        "The example has a separate random stream and is not one of the statistical trials. "
        "All panels share an intensity scale. Filtering changes the image before a pixel maximum "
        "is selected; the Gaussian fit instead fits the raw image.", "",
        "## Position error", "",
        "For each successful measurement, dx = estimated x - true x and dy = estimated y - true y. "
        "The radial error is sqrt(dx² + dy²). RMSE is sqrt(mean(dx² + dy²)) across trials. "
        "Smaller is better. All distances are in pixels; no physical pixel size is assumed.", "",
    ]
    for name in curve_paths:
        lines.extend([f"![Position RMSE by noise, spot width and position]({name})", ""])
    lines.extend([
        "Shading is a percentile bootstrap 95% interval for each method's RMSE. "
        "It describes Monte Carlo sampling uncertainty under this model, not uncertainty in an "
        "individual atom position. Zero-noise trials are identical and can have a zero-width interval. "
        "The plots use successful estimates; failure rates must be read alongside the errors. "
        "A formal method comparison would bootstrap paired trial differences; "
        "the individual intervals alone do not establish a difference between methods.", "",
        "## One preselected condition", "",
        f"Noise model: {first['noise_model']}; noise level: {first['noise_level']:g}; "
        f"spot width: {first['spot_sigma']:g} pixels; true centre: "
        f"({first['true_x']:g}, {first['true_y']:g}) pixels. "
        "This condition uses the middle entries of the configured width and noise lists, "
        "and the off-centre position. It was selected without reference to performance.", "",
        "| Method | RMSE (pixels) | 95% bootstrap interval (pixels) | Bias vector (pixels) | Failures |",
        "| --- | ---: | --- | --- | ---: |",
    ])
    for item in selected:
        def number(value):
            return "unavailable" if value is None else f"{value:.4f}"
        interval = f"{number(item['rmse_ci_low'])} to {number(item['rmse_ci_high'])}"
        lines.append(f"| {LABELS[item['method']]} | {number(item['rmse'])} | {interval} | "
                     f"({number(item['bias_x'])}, {number(item['bias_y'])}) | "
                     f"{item['n_trials'] - item['n_success']}/{item['n_trials']} |")
    lines.extend([
        "", "![Horizontal and vertical errors](error_cloud.png)", "",
        "The cloud's displacement from the origin indicates bias. Its spread indicates variation "
        "between trials. All four panels have identical limits, so a tight cloud may be hard to "
        "resolve beside a much larger error. Read the numerical summary as well.", "",
        "## Assumptions that affect the interpretation", "",
        "- The signal is a circular Gaussian sampled at pixel centres, with one isolated spot and "
        "uniform background. Pixels are not area-integrated; there is no scan drift, probe "
        "asymmetry, neighbouring atom, detector response or beam damage.",
        "- Gaussian noise is independent, additive and has standard deviation equal to the "
        "configured fraction of amplitude. Negative measured intensities are retained.",
        "- Poisson noise, when requested, generates counts from clean intensity times count scale, "
        "then rescales them. A higher count scale reduces relative fluctuations. This is a "
        "counting exercise, not a calibrated electron-dose model.",
        "- All methods receive exactly the same image in each trial. Only the centroid receives "
        "the true uniform background. The fitted centre, width, amplitude and background are "
        "estimated from data; the fit does not receive the true position or width.",
        "- The full-frame centroid subtracts background and clips negative weights. Retained "
        "positive noise can pull it towards the frame centre. A local-window centroid may behave "
        "differently; these results do not rank all centroiding methods.",
        "- Brightest-pixel methods return integer coordinates. Smoothing uses a fixed kernel of "
        f"width {config.smoothing_sigma:g} pixels and reflected boundaries. It does not remove pixel quantisation.",
        "- The fit uses the same functional model that generated the signal. This favours the "
        "model-based estimator. Ordinary least squares also does not implement the appropriate "
        "Poisson likelihood. Model mismatch is an important next experiment.",
        "- Optimiser non-convergence and active parameter bounds count as failures. Numerical "
        "convergence alone does not establish that a detected feature is an atom. "
        "There is no atom-detection confidence test in this project.",
        "- Spot amplitude is held constant as width varies, so wider spots contain more total "
        "signal. This is not a comparison at fixed total counts.", "",
        "## Inspect or reproduce", "",
        "`trials.csv` records every method result; missing estimates remain as failure rows. "
        "`summary.csv` and `summary.json` contain per-condition statistics. `metadata.json` records "
        "parameters, versions, seed and Git state. See the project README for commands and "
        "`docs/explanation.md` for the mathematical walkthrough.", "",
    ])
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
