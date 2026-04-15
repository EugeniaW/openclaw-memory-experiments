#!/usr/bin/env python3
"""Build a minimal CSV summary and markdown report for pilot fixtures."""

from __future__ import annotations

import csv
from pathlib import Path

from load_fixtures import FixtureRun, load_fixtures


REPORTS_DIR = Path("reports")
CSV_PATH = REPORTS_DIR / "pilot_summary.csv"
REPORT_PATH = REPORTS_DIR / "pilot_report.md"
FIXTURES_ROOT = Path("data/fixtures")
SUMMARY_FIELDS = [
    "run_id",
    "task_present",
    "output_present",
    "notes_present",
    "task_size_bytes",
    "output_size_bytes",
    "notes_size_bytes",
    "task_length_chars",
    "output_length_chars",
    "notes_length_chars",
    "all_expected_files_present",
    "task_nonempty",
    "output_nonempty",
    "notes_nonempty",
    "has_any_content",
    "is_minimally_complete",
]


def normalize_run(run: FixtureRun) -> dict[str, object]:
    task_present = run.task_prompt.exists
    output_present = run.final_output.exists
    notes_present = run.notes.exists

    task_nonempty = run.task_prompt.text_length > 0
    output_nonempty = run.final_output.text_length > 0
    notes_nonempty = run.notes.text_length > 0

    return {
        "run_id": run.run_id,
        "task_present": task_present,
        "output_present": output_present,
        "notes_present": notes_present,
        "task_size_bytes": run.task_prompt.size_bytes,
        "output_size_bytes": run.final_output.size_bytes,
        "notes_size_bytes": run.notes.size_bytes,
        "task_length_chars": run.task_prompt.text_length,
        "output_length_chars": run.final_output.text_length,
        "notes_length_chars": run.notes.text_length,
        "all_expected_files_present": task_present and output_present and notes_present,
        "task_nonempty": task_nonempty,
        "output_nonempty": output_nonempty,
        "notes_nonempty": notes_nonempty,
        "has_any_content": task_nonempty or output_nonempty or notes_nonempty,
        "is_minimally_complete": task_nonempty and output_nonempty,
    }


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def build_report(rows: list[dict[str, object]]) -> str:
    total_runs = len(rows)
    present_count = sum(1 for row in rows if row["all_expected_files_present"])
    minimally_complete_count = sum(1 for row in rows if row["is_minimally_complete"])
    any_content_count = sum(1 for row in rows if row["has_any_content"])

    lines = [
        "# Pilot Fixture Report",
        "",
        "## Scope",
        "",
        f"This report summarizes the pilot fixtures currently present under `{FIXTURES_ROOT}`.",
        "It reports only directly observable fixture properties such as file presence and content length.",
        "It does not infer run behavior, memory quality, or experimental findings beyond the available files.",
        "",
        "## Fixtures Present",
        "",
        f"- Fixture directories found: {total_runs}",
        f"- Runs with all expected files present: {present_count}",
        f"- Runs with non-empty task and output files: {minimally_complete_count}",
        f"- Runs with any non-empty file content: {any_content_count}",
        "",
        "| run_id | task | output | notes | task chars | output chars | notes chars | minimally complete |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]

    for row in rows:
        lines.append(
            "| {run_id} | {task_present} | {output_present} | {notes_present} | "
            "{task_length_chars} | {output_length_chars} | {notes_length_chars} | {is_minimally_complete} |".format(
                **row
            )
        )

    missing_observations = []
    for row in rows:
        missing_parts = []
        if not row["task_present"]:
            missing_parts.append("missing task_prompt.md")
        elif not row["task_nonempty"]:
            missing_parts.append("empty task_prompt.md")

        if not row["output_present"]:
            missing_parts.append("missing final_output.md")
        elif not row["output_nonempty"]:
            missing_parts.append("empty final_output.md")

        if not row["notes_present"]:
            missing_parts.append("missing notes.md")
        elif not row["notes_nonempty"]:
            missing_parts.append("empty notes.md")

        if missing_parts:
            missing_observations.append(f"- `{row['run_id']}`: " + ", ".join(missing_parts))

    lines.extend(["", "## What Is Missing", ""])
    if missing_observations:
        lines.extend(missing_observations)
    else:
        lines.append("- No missing or empty expected files were observed in the current fixtures.")

    lines.extend(
        [
            "",
            "## What A Full Memory Experiment Would Need Next",
            "",
            "- More non-empty pilot fixtures with preserved task prompts, outputs, and notes for each run.",
            "- A stable fixture schema or manifest that records run metadata explicitly rather than inferring from directory names.",
            "- Clear evaluation fields for memory-specific observations that can be checked without inventing missing run details.",
            "- A documented procedure for syncing or copying approved fixtures from the separate dataset repo into this repo.",
            "- Additional validation and reporting once real run content exists in the pilot fixtures.",
            "",
            "## Traceability",
            "",
            f"- Source fixtures: `{FIXTURES_ROOT}`",
            f"- CSV summary: `{CSV_PATH}`",
            "- Generated from observable file presence and lengths only.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_report(path: Path, content: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    runs = load_fixtures(FIXTURES_ROOT)
    rows = [normalize_run(run) for run in runs]
    write_csv(rows, CSV_PATH)
    write_report(REPORT_PATH, build_report(rows))


if __name__ == "__main__":
    main()
