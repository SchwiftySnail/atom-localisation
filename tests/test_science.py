"""Checks for coordinate conventions, noise statistics and error calculations."""

import numpy as np
import pytest

from atom_localisation.estimators import brightest_pixel, centroid, gaussian_fit, smoothed_peak
from atom_localisation.experiment import Config, run_experiment, summarise
from atom_localisation.model import add_noise, gaussian_image


def test_coordinates_are_xy_and_shape_is_rows_columns():
    image = gaussian_image((25, 39), (27, 9), 1.5)
    assert image.shape == (25, 39)
    assert image[9, 27] == pytest.approx(1.05)
    estimate = brightest_pixel(image)
    assert (estimate.x, estimate.y) == (27, 9)


def test_noise_free_fit_recovers_fractional_centre_without_receiving_truth():
    image = gaussian_image((33, 49), (12.35, 19.65), 2.7, amplitude=1.4, background=0.2)
    estimate = gaussian_fit(image)
    assert estimate.success
    assert estimate.x == pytest.approx(12.35, abs=1e-5)
    assert estimate.y == pytest.approx(19.65, abs=1e-5)


def test_brightest_pixel_has_fractional_position_error_even_without_noise():
    estimate = brightest_pixel(gaussian_image((33, 33), (16.35, 15.65), 2))
    assert (estimate.x, estimate.y) == (16, 16)
    assert np.hypot(estimate.x - 16.35, estimate.y - 15.65) == pytest.approx(np.sqrt(2) * 0.35)


def test_centroid_on_clean_well_contained_spot():
    estimate = centroid(gaussian_image((49, 49), (23.35, 24.65), 2), background=0.05)
    assert estimate.x == pytest.approx(23.35, abs=1e-8)
    assert estimate.y == pytest.approx(24.65, abs=1e-8)


def test_centroid_full_frame_positive_weights_can_pull_towards_frame_centre():
    image = gaussian_image((49, 49), (12, 12), 1.5, background=0)
    # A deterministic positive pedestal isolates the source of the bias.
    clean = centroid(image, background=0)
    contaminated = centroid(image + 0.02, background=0)
    assert clean.x == pytest.approx(12, abs=1e-8)
    assert clean.x < contaminated.x < 24
    assert clean.y < contaminated.y < 24


@pytest.mark.parametrize("method", [brightest_pixel, smoothed_peak, centroid, gaussian_fit])
def test_constant_image_is_an_explicit_failure(method):
    estimate = method(np.ones((17, 17)))
    assert not estimate.success
    assert estimate.failure == "constant_image"


def test_noise_does_not_mutate_clean_image_and_is_seeded():
    clean = gaussian_image((17, 17), (8.3, 8.7), 2)
    original = clean.copy()
    a = add_noise(clean, "gaussian", 0.1, np.random.default_rng(42))
    b = add_noise(clean, "gaussian", 0.1, np.random.default_rng(42))
    np.testing.assert_array_equal(a, b)
    np.testing.assert_array_equal(clean, original)
    assert np.any(a < 0)  # Negative Gaussian measurements have not been clipped.
    np.testing.assert_array_equal(add_noise(clean, "gaussian", 0, np.random.default_rng(1)), clean)


def test_gaussian_noise_scale_and_mean():
    observed = add_noise(np.zeros((300, 300)), "gaussian", 0.1, np.random.default_rng(3), amplitude=2)
    assert abs(observed.mean()) < 0.003
    assert observed.std() == pytest.approx(0.2, abs=0.003)


def test_rescaled_poisson_noise_mean_and_variance():
    observed = add_noise(np.full((300, 300), 0.4), "poisson", 20, np.random.default_rng(3))
    assert observed.mean() == pytest.approx(0.4, abs=0.003)
    assert observed.var() == pytest.approx(0.4 / 20, abs=0.001)


def test_summary_rmse_is_not_mean_radial_error_and_retains_failures():
    base = dict(scenario_id=0, noise_model="gaussian", noise_level=0.1, spot_sigma=2,
                position="integer", true_x=8, true_y=8, method="example")
    rows = [
        dict(base, success=True, dx=0, dy=0, error=0),
        dict(base, success=True, dx=3, dy=4, error=5),
        dict(base, success=False, dx=None, dy=None, error=None),
    ]
    result = summarise(rows, bootstrap_samples=100)[0]
    assert result["mean_error"] == 2.5
    assert result["rmse"] == pytest.approx(np.sqrt(12.5))
    assert result["bias_x"] == 1.5
    assert result["bias_y"] == 2
    assert result["n_trials"] == 3
    assert result["n_success"] == 2
    assert result["failure_rate"] == pytest.approx(1 / 3)
    assert result["rmse_ci_low"] <= result["rmse"] <= result["rmse_ci_high"]


def test_all_failed_summary_uses_missing_values_not_false_zero_errors():
    row = dict(scenario_id=0, noise_model="gaussian", noise_level=1, spot_sigma=2,
               position="integer", true_x=8, true_y=8, method="example", success=False)
    result = summarise([row], bootstrap_samples=100)[0]
    assert result["rmse"] is None
    assert result["failure_rate"] == 1


def test_experiment_is_reproducible_and_trial_ids_pair_methods():
    config = Config(trials=2, size=17, sigmas=(1.5,), noise_levels=(0.05,), bootstrap_samples=100)
    first = run_experiment(config)
    assert first == run_experiment(config)
    assert len(first) == 3 * 2 * 4
    for offset in range(0, len(first), 4):
        group = first[offset:offset + 4]
        assert len({(row["scenario_id"], row["trial"]) for row in group}) == 1
        assert len({row["method"] for row in group}) == 4


@pytest.mark.parametrize("changes", [
    {"trials": 1}, {"size": 16}, {"seed": -1}, {"sigmas": (float("nan"),)},
    {"sigmas": (20,)}, {"noise_levels": (-0.1,)}, {"count_scales": (0,)},
    {"background": -1}, {"amplitude": 0}, {"noise_models": ()},
    {"noise_models": ("gaussian", "gaussian")}, {"smoothing_sigma": 0},
])
def test_invalid_config_is_rejected(changes):
    with pytest.raises(ValueError):
        Config(**changes).validate()


@pytest.mark.parametrize("image", [np.array([1, 2]), np.full((3, 3), np.nan)])
def test_invalid_image_is_rejected(image):
    with pytest.raises(ValueError):
        gaussian_fit(image)
