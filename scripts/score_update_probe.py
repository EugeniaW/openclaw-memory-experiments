#!/usr/bin/env python3
"""Score raw update probe outputs with simple rule-based checks."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


SCENARIOS_PATH = Path("benchmarks/update_probe/scenarios.json")
RAW_DIR = Path("eval/update_probe/raw")
RESULTS_PATH = Path("eval/update_probe/results.csv")
SUMMARY_PATH = Path("eval/update_probe/summary.md")
RESULT_FIELDS = [
    "scenario_id",
    "domain",
    "mode",
    "latest_fact_fidelity",
    "stale_fact_usage",
    "decision_use_rate",
    "contradiction_count",
    "update_sensitivity",
    "storage_failure",
    "application_failure",
    "consistency_failure",
    "raw_output_path",
]


def load_scenarios(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(text: str) -> str:
    lowered = text.lower()
    chars = [char if char.isalnum() else " " for char in lowered]
    return " ".join("".join(chars).split())


def contains_phrase(text: str, phrase: str) -> bool:
    return normalize_text(phrase) in normalize_text(text)


def ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 3)


def load_raw_output(raw_dir: Path, scenario_id: str) -> dict | None:
    path = raw_dir / f"{scenario_id}.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["_path"] = str(path)
    return payload


def extract_scored_text(response: str) -> str:
    sections: list[str] = []
    current_header = ""
    current_lines: list[str] = []

    def flush() -> None:
        if current_header in {"## latest facts", "## decision", "## rationale"}:
            sections.extend(current_lines)

    for raw_line in response.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            flush()
            current_header = line.lower()
            current_lines = []
        else:
            current_lines.append(line)
    flush()

    if sections:
        return "\n".join(sections)
    return response


def score_scenario(scenario: dict, raw_payload: dict | None) -> dict[str, object]:
    response = ""
    mode = "missing"
    raw_output_path = ""
    if raw_payload:
        response = raw_payload.get("response", "")
        mode = raw_payload.get("mode", "unknown")
        raw_output_path = raw_payload.get("_path", "")

    scored_text = extract_scored_text(response)

    latest_matches = sum(
        1 for fact in scenario["expected_latest_facts"] if contains_phrase(scored_text, fact)
    )
    latest_fact_fidelity = ratio(latest_matches, len(scenario["expected_latest_facts"]))

    stale_facts = [update["old_fact"] for update in scenario["updates"]]
    stale_matches = sum(1 for fact in stale_facts if contains_phrase(scored_text, fact))
    stale_fact_usage = ratio(stale_matches, len(stale_facts))

    contradiction_count = 0
    for update in scenario["updates"]:
        if contains_phrase(scored_text, update["old_fact"]) and contains_phrase(scored_text, update["new_fact"]):
            contradiction_count += 1

    implication = scenario["expected_decision_implications"]
    action_hit = any(
        contains_phrase(scored_text, phrase) for phrase in implication["recommended_action_keywords"]
    )
    stale_action_hit = any(
        contains_phrase(scored_text, phrase) for phrase in implication["stale_action_keywords"]
    )
    rationale_hit = any(
        contains_phrase(scored_text, phrase) for phrase in implication["required_rationale_keywords"]
    ) or latest_matches > 0

    decision_use_rate = 1 if action_hit and rationale_hit else 0
    update_sensitivity = 1 if action_hit and not stale_action_hit else 0

    storage_failure = 1 if latest_fact_fidelity < 1.0 else 0
    application_failure = 1 if latest_fact_fidelity == 1.0 and decision_use_rate == 0 else 0
    consistency_failure = 1 if contradiction_count > 0 or stale_fact_usage > 0 else 0

    return {
        "scenario_id": scenario["scenario_id"],
        "domain": scenario["domain"],
        "mode": mode,
        "latest_fact_fidelity": latest_fact_fidelity,
        "stale_fact_usage": stale_fact_usage,
        "decision_use_rate": decision_use_rate,
        "contradiction_count": contradiction_count,
        "update_sensitivity": update_sensitivity,
        "storage_failure": storage_failure,
        "application_failure": application_failure,
        "consistency_failure": consistency_failure,
        "raw_output_path": raw_output_path,
    }


def write_results(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def average(rows: list[dict[str, object]], key: str) -> float:
    if not rows:
        return 0.0
    return round(sum(float(row[key]) for row in rows) / len(rows), 3)


def total(rows: list[dict[str, object]], key: str) -> int:
    return sum(int(row[key]) for row in rows)


def build_summary(rows: list[dict[str, object]], scenarios_path: Path, raw_dir: Path, results_path: Path) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Temporal Update + Decision Utility Probe Summary",
        "",
        f"Generated: {timestamp}",
        "",
        "## Scope",
        "",
        "- This summary reports direct rule-based checks over six hand-curated pilot scenarios.",
        "- It does not claim statistical significance or infer behavior beyond the observed outputs.",
        "",
        "## Aggregate Metrics",
        "",
        f"- Scenarios scored: {len(rows)}",
        f"- Average latest fact fidelity: {average(rows, 'latest_fact_fidelity')}",
        f"- Average stale fact usage: {average(rows, 'stale_fact_usage')}",
        f"- Decision use rate: {average(rows, 'decision_use_rate')}",
        f"- Total contradiction count: {total(rows, 'contradiction_count')}",
        f"- Update sensitivity: {average(rows, 'update_sensitivity')}",
        "",
        "## Failure Signals",
        "",
        f"- Storage failures: {total(rows, 'storage_failure')}",
        f"- Application failures: {total(rows, 'application_failure')}",
        f"- Consistency failures: {total(rows, 'consistency_failure')}",
        "",
        "## Traceability",
        "",
        f"- Scenario source: `{scenarios_path}`",
        f"- Raw outputs: `{raw_dir}`",
        f"- Results CSV: `{results_path}`",
        "- Scores come from exact or near-exact phrase checks over the saved raw responses.",
    ]
    return "\n".join(lines) + "\n"


def write_summary(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=Path, default=SCENARIOS_PATH)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--results", type=Path, default=RESULTS_PATH)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    args = parser.parse_args()

    scenarios = load_scenarios(args.scenarios)
    rows = [
        score_scenario(scenario, load_raw_output(args.raw_dir, scenario["scenario_id"]))
        for scenario in scenarios
    ]
    write_results(rows, args.results)
    write_summary(
        args.summary,
        build_summary(rows, args.scenarios, args.raw_dir, args.results),
    )


if __name__ == "__main__":
    main()
