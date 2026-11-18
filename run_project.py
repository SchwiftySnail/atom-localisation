"""Run the full synthetic localisation experiment from the command line."""

import argparse
from pathlib import Path

from atom_localisation.experiment import Config, run_experiment, summarise
from atom_localisation.plots import save_error_cloud, save_error_curves, save_example
from atom_localisation.report import write_outputs


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=100, help="realisations per condition (at least 2)")
    parser.add_argument("--seed", type=int, default=2027)
    parser.add_argument("--size", type=int, default=33, help="odd image side length, at least 17 pixels")
    parser.add_argument("--sigmas", type=float, nargs="+", default=[1, 2, 3], help="spot widths in pixels")
    parser.add_argument("--noise-models", choices=["gaussian", "poisson"], nargs="+", default=["gaussian"])
    parser.add_argument("--noise-levels", type=float, nargs="+", default=[0, 0.02, 0.05, 0.1, 0.2],
                        help="Gaussian noise SD as a fraction of amplitude")
    parser.add_argument("--count-scales", type=float, nargs="+", default=[10, 50, 200],
                        help="Poisson counts per unit clean intensity")
    parser.add_argument("--amplitude", type=float, default=1.0)
    parser.add_argument("--background", type=float, default=0.05)
    parser.add_argument("--smoothing-sigma", type=float, default=1.0, help="filter width in pixels")
    parser.add_argument("--bootstrap-samples", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=Path("outputs/experiment"),
                        help="output folder; rerunning replaces generated files with the same names")
    args = parser.parse_args()
    config = Config(
        trials=args.trials, seed=args.seed, size=args.size, sigmas=tuple(args.sigmas),
        noise_models=tuple(args.noise_models), noise_levels=tuple(args.noise_levels),
        count_scales=tuple(args.count_scales), amplitude=args.amplitude, background=args.background,
        smoothing_sigma=args.smoothing_sigma, bootstrap_samples=args.bootstrap_samples,
    )
    try:
        config.validate()
    except ValueError as error:
        parser.error(str(error))
    return config, args.output.resolve()


def main():
    config, output = parse_args()
    output.mkdir(parents=True, exist_ok=True)

    def progress(done, total, model, sigma, position, level):
        print(f"[{done}/{total}] {model}, width={sigma:g}, {position}, level={level:g}", flush=True)

    rows = run_experiment(config, progress)
    summaries = summarise(rows, config.seed, config.bootstrap_samples)
    save_example(config, output)
    curves = save_error_curves(config, summaries, output)
    save_error_cloud(config, rows, output)
    write_outputs(config, rows, summaries, output, curves)
    failures = sum(not row["success"] for row in rows)
    print(f"\nFinished: {len(rows):,} estimates; {failures:,} failures retained in the results.")
    print(f"Read the report: {output / 'report.md'}")


if __name__ == "__main__":
    main()
