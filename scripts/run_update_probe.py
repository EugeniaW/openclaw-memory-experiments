#!/usr/bin/env python3
"""Run the temporal update probe in mock, manual, or CLI mode."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCENARIOS_PATH = Path("benchmarks/update_probe/scenarios.json")
EVAL_DIR = Path("eval/update_probe")
RAW_DIR = EVAL_DIR / "raw"
RUN_LOG_PATH = EVAL_DIR / "run_log.jsonl"
RUN_METADATA_PATH = EVAL_DIR / "run_metadata.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_run_id() -> str:
    return datetime.now(timezone.utc).strftime("update-probe-%Y%m%dT%H%M%SZ")


def load_scenarios(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_prompt(scenario: dict) -> str:
    lines = [
        "You are reviewing a business situation with updated facts.",
        "Use the latest updates when making the final recommendation.",
        "Do not rely on superseded facts.",
        "",
        f"Scenario ID: {scenario['scenario_id']}",
        f"Domain: {scenario['domain']}",
        f"Topic: {scenario['topic']}",
        "",
        "Initial facts:",
    ]
    lines.extend(f"- {fact}" for fact in scenario["initial_facts"])
    lines.append("")
    lines.append("Updated facts:")
    lines.extend(f"- {update['new_fact']}" for update in scenario["updates"])
    lines.append("")
    lines.append("Distractors:")
    lines.extend(f"- {fact}" for fact in scenario["distractors"])
    lines.extend(
        [
            "",
            "Task: recommend the next business decision.",
            "Return exactly these sections:",
            "## Latest Facts",
            "- List the newest facts you are using.",
            "## Decision",
            "- Give one clear recommendation.",
            "## Rationale",
            "- Explain why the latest facts change the decision.",
            "## Stale Facts To Avoid",
            "- Name any earlier assumptions that should no longer drive the decision.",
        ]
    )
    return "\n".join(lines) + "\n"


def mock_response(scenario: dict) -> str:
    decision = scenario["expected_decision_implications"]["recommended_action_keywords"][0]
    stale = scenario["expected_decision_implications"]["stale_action_keywords"][0]
    lines = ["## Latest Facts"]
    lines.extend(f"- {fact}" for fact in scenario["expected_latest_facts"])
    lines.extend(
        [
            "## Decision",
            f"- {decision}.",
            "## Rationale",
        ]
    )
    lines.extend(
        f"- {fact}" for fact in scenario["expected_decision_implications"]["required_rationale_keywords"]
    )
    lines.extend(
        [
            "## Stale Facts To Avoid",
            f"- Do not rely on: {stale}.",
        ]
    )
    return "\n".join(lines) + "\n"


def read_manual_response(scenario: dict, prompt: str, end_marker: str) -> tuple[str, str, str, str]:
    prompt_shown_at = utc_now_iso()
    print("")
    print(f"===== {scenario['scenario_id']} =====")
    print(prompt)
    print(
        f"Paste the model response for {scenario['scenario_id']}. End with a line containing only {end_marker}."
    )
    response_started_at = utc_now_iso()
    collected: list[str] = []
    while True:
        try:
            line = input()
        except EOFError as exc:
            raise SystemExit("Manual mode ended before all scenarios were captured.") from exc
        if line.strip() == end_marker:
            break
        collected.append(line)
    response_ended_at = utc_now_iso()
    response = "\n".join(collected).strip()
    raw_response = (response + "\n") if response else ""
    return raw_response, prompt_shown_at, response_started_at, response_ended_at


def run_cli_command(command: str, prompt: str) -> tuple[str, str, int]:
    completed = subprocess.run(
        command,
        input=prompt,
        text=True,
        shell=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout, completed.stderr, completed.returncode


def save_raw_output(raw_dir: Path, payload: dict) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{payload['scenario_id']}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def append_run_log(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_run_metadata(
    path: Path,
    run_id: str,
    mode: str,
    started_at: str,
    ended_at: str,
    scenario_count: int,
    command: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "mode": mode,
        "started_at": started_at,
        "ended_at": ended_at,
        "scenario_count": scenario_count,
        "command": command,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_scenarios(
    scenarios: list[dict],
    mode: str,
    raw_dir: Path,
    cli_command: str | None,
    end_marker: str,
    run_id: str,
    run_log_path: Path,
) -> None:
    run_log_path.parent.mkdir(parents=True, exist_ok=True)
    run_log_path.write_text("", encoding="utf-8")

    for scenario in scenarios:
        prompt = build_prompt(scenario)
        prompt_shown_at = utc_now_iso()
        response_started_at = prompt_shown_at
        response_ended_at = prompt_shown_at
        stderr_text = ""
        return_code = 0

        if mode == "mock":
            response = mock_response(scenario)
            response_ended_at = utc_now_iso()
        elif mode == "manual":
            response, prompt_shown_at, response_started_at, response_ended_at = read_manual_response(
                scenario,
                prompt,
                end_marker,
            )
        else:
            if not cli_command:
                raise SystemExit("--cli-command is required when --mode=cli")
            response_started_at = utc_now_iso()
            response, stderr_text, return_code = run_cli_command(cli_command, prompt)
            response_ended_at = utc_now_iso()

        payload = {
            "scenario_id": scenario["scenario_id"],
            "topic": scenario["topic"],
            "prompt_text": prompt,
            "prompt_shown_at": prompt_shown_at,
            "response_started_at": response_started_at,
            "response_ended_at": response_ended_at,
            "raw_response": response,
            "mode": mode,
            "run_id": run_id,
            "response": response,
            "prompt": prompt,
            "stderr": stderr_text,
            "return_code": return_code,
        }
        path = save_raw_output(raw_dir, payload)
        append_run_log(run_log_path, payload)
        print(f"saved {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=Path, default=SCENARIOS_PATH)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument(
        "--mode",
        choices=("mock", "manual", "cli"),
        default="mock",
        help="mock writes deterministic placeholder outputs; manual collects pasted responses; cli sends prompts to a command.",
    )
    parser.add_argument(
        "--cli-command",
        help="Shell command to execute in CLI mode. The prompt is sent to stdin.",
    )
    parser.add_argument(
        "--manual-end-marker",
        default="__END__",
        help="Line marker used to end pasted responses in manual mode.",
    )
    parser.add_argument("--run-log", type=Path, default=RUN_LOG_PATH)
    parser.add_argument("--run-metadata", type=Path, default=RUN_METADATA_PATH)
    args = parser.parse_args()

    scenarios = load_scenarios(args.scenarios)
    run_id = build_run_id()
    started_at = utc_now_iso()
    command = " ".join(sys.argv)

    run_scenarios(
        scenarios=scenarios,
        mode=args.mode,
        raw_dir=args.raw_dir,
        cli_command=args.cli_command,
        end_marker=args.manual_end_marker,
        run_id=run_id,
        run_log_path=args.run_log,
    )

    ended_at = utc_now_iso()
    write_run_metadata(
        path=args.run_metadata,
        run_id=run_id,
        mode=args.mode,
        started_at=started_at,
        ended_at=ended_at,
        scenario_count=len(scenarios),
        command=command,
    )


if __name__ == "__main__":
    main()
