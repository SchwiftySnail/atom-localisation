"""End-to-end check: a small experiment produces usable data and figures."""

import csv
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_small_complete_run(tmp_path):
    subprocess.run([
        sys.executable, str(ROOT / "run_project.py"), "--trials", "2", "--size", "17",
        "--sigmas", "1.5", "--noise-models", "gaussian", "poisson",
        "--noise-levels", "0.05", "--count-scales", "50", "--bootstrap-samples", "100",
        "--output", str(tmp_path),
    ], check=True, capture_output=True, text=True, cwd=ROOT)
    with (tmp_path / "trials.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2 * 3 * 2 * 4
    assert {row["noise_model"] for row in rows} == {"gaussian", "poisson"}
    summaries = json.loads((tmp_path / "summary.json").read_text())
    assert len(summaries) == 2 * 3 * 4
    metadata = json.loads((tmp_path / "metadata.json").read_text())
    assert metadata["configuration"]["seed"] == 2027
    assert metadata["numpy"]
    for name in ("example.png", "gaussian_error_curves.png", "poisson_error_curves.png", "error_cloud.png"):
        assert (tmp_path / name).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Assumptions" in (tmp_path / "report.md").read_text()


def test_cli_rejects_invalid_trials_without_creating_output(tmp_path):
    output = tmp_path / "not-created"
    result = subprocess.run([sys.executable, str(ROOT / "run_project.py"), "--trials", "0",
                             "--output", str(output)], capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 2
    assert "at least 2" in result.stderr
    assert not output.exists()
