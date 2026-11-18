"""Run paired Monte Carlo trials and retain every estimate, including failures."""

from dataclasses import asdict, dataclass
from itertools import product

import numpy as np

from .estimators import estimate_all
from .model import add_noise, gaussian_image


@dataclass(frozen=True)
class Config:
    trials: int = 100
    seed: int = 2027
    size: int = 33
    amplitude: float = 1.0
    background: float = 0.05
    sigmas: tuple = (1.0, 2.0, 3.0)
    noise_models: tuple = ("gaussian",)
    noise_levels: tuple = (0.0, 0.02, 0.05, 0.1, 0.2)
    count_scales: tuple = (10.0, 50.0, 200.0)
    smoothing_sigma: float = 1.0
    bootstrap_samples: int = 1000

    def validate(self):
        if not isinstance(self.trials, int) or self.trials < 2:
            raise ValueError("trials must be an integer of at least 2")
        if not isinstance(self.size, int) or self.size < 17 or self.size % 2 == 0:
            raise ValueError("size must be an odd integer of at least 17")
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("seed must be a non-negative integer")
        if not isinstance(self.bootstrap_samples, int) or self.bootstrap_samples < 100:
            raise ValueError("bootstrap_samples must be an integer of at least 100")
        if not self.noise_models or len(set(self.noise_models)) != len(self.noise_models):
            raise ValueError("choose at least one noise model, without duplicates")
        if any(model not in ("gaussian", "poisson") for model in self.noise_models):
            raise ValueError("noise models must be gaussian or poisson")
        for name, values, allow_zero in (
            ("sigmas", self.sigmas, False),
            ("noise_levels", self.noise_levels, True),
            ("count_scales", self.count_scales, False),
        ):
            if not values or len(set(values)) != len(values):
                raise ValueError(f"{name} must be non-empty and contain no duplicates")
            if any(not np.isfinite(v) or (v < 0 if allow_zero else v <= 0) for v in values):
                raise ValueError(f"invalid {name}")
        if max(self.sigmas) >= self.size / 3:
            raise ValueError("spot widths must be smaller than size / 3 (the fit's upper bound)")
        if not np.isfinite(self.smoothing_sigma) or self.smoothing_sigma <= 0:
            raise ValueError("smoothing_sigma must be positive and finite")
        gaussian_image((self.size, self.size), self.positions()["integer"], self.sigmas[0],
                       self.amplitude, self.background)

    def positions(self):
        middle = (self.size - 1) / 2
        return {
            "integer": (middle, middle),
            "fractional": (middle + 0.35, middle - 0.35),
            "off_centre": (middle - 3.65, middle + 3.65),
        }

    def scenarios(self):
        for model in self.noise_models:
            levels = self.noise_levels if model == "gaussian" else self.count_scales
            for sigma, position, level in product(self.sigmas, self.positions(), levels):
                yield model, float(sigma), position, float(level)

    def to_dict(self):
        return {**asdict(self), "positions_xy": self.positions()}


def run_experiment(config, progress=None):
    config.validate()
    scenarios = list(config.scenarios())
    seeds = np.random.SeedSequence(config.seed).spawn(len(scenarios))
    rows = []
    for scenario_id, ((model, sigma, position, level), seed) in enumerate(zip(scenarios, seeds)):
        true_x, true_y = config.positions()[position]
        clean = gaussian_image((config.size, config.size), (true_x, true_y), sigma,
                               config.amplitude, config.background)
        rng = np.random.default_rng(seed)
        for trial in range(config.trials):
            observed = add_noise(clean, model, level, rng, config.amplitude)
            estimates = estimate_all(observed, config.background, config.smoothing_sigma)
            for method, estimate in estimates.items():
                dx = estimate.x - true_x if estimate.success else None
                dy = estimate.y - true_y if estimate.success else None
                rows.append({
                    "scenario_id": scenario_id,
                    "noise_model": model,
                    "noise_level": level,
                    "spot_sigma": sigma,
                    "position": position,
                    "trial": trial,
                    "method": method,
                    "true_x": true_x,
                    "true_y": true_y,
                    "estimated_x": estimate.x,
                    "estimated_y": estimate.y,
                    "success": estimate.success,
                    "failure": estimate.failure,
                    "dx": dx,
                    "dy": dy,
                    "error": float(np.hypot(dx, dy)) if estimate.success else None,
                })
        if progress:
            progress(scenario_id + 1, len(scenarios), model, sigma, position, level)
    return rows


def summarise(rows, seed=2027, bootstrap_samples=1000):
    groups = {}
    for row in rows:
        groups.setdefault((row["scenario_id"], row["method"]), []).append(row)
    rng = np.random.default_rng(np.random.SeedSequence([seed, 101]))
    summaries = []
    for (_, method), group in groups.items():
        successful = [row for row in group if row["success"]]
        first = group[0]
        result = {key: first[key] for key in (
            "scenario_id", "noise_model", "noise_level", "spot_sigma", "position", "true_x", "true_y"
        )}
        result.update(method=method, n_trials=len(group), n_success=len(successful),
                      failure_rate=1 - len(successful) / len(group))
        metrics = ("mean_error", "median_error", "p95_error", "rmse", "rmse_ci_low", "rmse_ci_high",
                   "bias_x", "bias_y", "bias_distance", "std_x", "std_y")
        result.update(dict.fromkeys(metrics))
        if successful:
            errors = np.array([row["error"] for row in successful])
            dx = np.array([row["dx"] for row in successful])
            dy = np.array([row["dy"] for row in successful])
            bias_x, bias_y = float(dx.mean()), float(dy.mean())
            result.update(
                mean_error=float(errors.mean()), median_error=float(np.median(errors)),
                p95_error=float(np.quantile(errors, 0.95)),
                rmse=float(np.sqrt(np.mean(errors**2))), bias_x=bias_x, bias_y=bias_y,
                bias_distance=float(np.hypot(bias_x, bias_y)),
                std_x=float(dx.std(ddof=1)) if len(dx) > 1 else None,
                std_y=float(dy.std(ddof=1)) if len(dy) > 1 else None,
            )
            if len(errors) > 1:
                indices = rng.integers(0, len(errors), size=(bootstrap_samples, len(errors)))
                boot_rmse = np.sqrt(np.mean(errors[indices] ** 2, axis=1))
                lo, hi = np.quantile(boot_rmse, [0.025, 0.975])
                result.update(rmse_ci_low=float(lo), rmse_ci_high=float(hi))
        summaries.append(result)
    return summaries
