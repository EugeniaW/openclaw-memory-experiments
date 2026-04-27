#!/usr/bin/env python3
"""Plot simple update probe charts from the scored CSV results."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


RESULTS_PATH = Path("eval/update_probe/results.csv")
FIDELITY_PLOT_PATH = Path("eval/update_probe/latest_fact_fidelity.png")
FAILURE_PLOT_PATH = Path("eval/update_probe/failure_breakdown.png")


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def require_matplotlib():
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise SystemExit(
            "matplotlib is required for plot generation. Install it before running scripts/plot_update_probe.py."
        ) from exc
    return plt


def plot_latest_fact_fidelity(rows: list[dict[str, str]], path: Path) -> None:
    plt = require_matplotlib()
    scenario_ids = [row["scenario_id"] for row in rows]
    scores = [float(row["latest_fact_fidelity"]) for row in rows]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(scenario_ids, scores, color="#2f6db0")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Fidelity")
    ax.set_title("Latest Fact Fidelity by Scenario")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_failure_breakdown(rows: list[dict[str, str]], path: Path) -> None:
    plt = require_matplotlib()
    labels = ["storage", "application", "consistency"]
    values = [
        sum(int(row["storage_failure"]) for row in rows),
        sum(int(row["application_failure"]) for row in rows),
        sum(int(row["consistency_failure"]) for row in rows),
    ]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, values, color=["#c45b5b", "#d39c3f", "#7a5cc2"])
    ax.set_ylabel("Scenario Count")
    ax.set_title("Failure Breakdown")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS_PATH)
    parser.add_argument("--fidelity-plot", type=Path, default=FIDELITY_PLOT_PATH)
    parser.add_argument("--failure-plot", type=Path, default=FAILURE_PLOT_PATH)
    args = parser.parse_args()

    rows = load_rows(args.results)
    plot_latest_fact_fidelity(rows, args.fidelity_plot)
    plot_failure_breakdown(rows, args.failure_plot)


if __name__ == "__main__":
    main()
