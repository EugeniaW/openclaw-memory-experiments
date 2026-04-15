#!/usr/bin/env python3
"""Load hand-curated pilot fixtures from data/fixtures."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path


EXPECTED_FILES = ("task_prompt.md", "final_output.md", "notes.md")


@dataclass
class FixtureFile:
    name: str
    path: str
    exists: bool
    size_bytes: int
    text_length: int
    content: str


@dataclass
class FixtureRun:
    run_id: str
    path: str
    task_prompt: FixtureFile
    final_output: FixtureFile
    notes: FixtureFile


def read_fixture_file(path: Path) -> FixtureFile:
    if not path.exists():
        return FixtureFile(
            name=path.name,
            path=str(path),
            exists=False,
            size_bytes=0,
            text_length=0,
            content="",
        )

    content = path.read_text(encoding="utf-8")
    return FixtureFile(
        name=path.name,
        path=str(path),
        exists=True,
        size_bytes=path.stat().st_size,
        text_length=len(content),
        content=content,
    )


def load_fixture_run(run_dir: Path) -> FixtureRun:
    return FixtureRun(
        run_id=run_dir.name,
        path=str(run_dir),
        task_prompt=read_fixture_file(run_dir / "task_prompt.md"),
        final_output=read_fixture_file(run_dir / "final_output.md"),
        notes=read_fixture_file(run_dir / "notes.md"),
    )


def load_fixtures(fixtures_root: Path) -> list[FixtureRun]:
    if not fixtures_root.exists():
        return []

    runs = []
    for child in sorted(fixtures_root.iterdir()):
        if child.is_dir():
            runs.append(load_fixture_run(child))
    return runs


def fixture_run_to_dict(run: FixtureRun) -> dict:
    payload = asdict(run)
    payload["expected_files"] = list(EXPECTED_FILES)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixtures-root",
        type=Path,
        default=Path("data/fixtures"),
        help="Directory containing pilot fixture runs.",
    )
    args = parser.parse_args()

    runs = load_fixtures(args.fixtures_root)
    print(json.dumps([fixture_run_to_dict(run) for run in runs], indent=2))


if __name__ == "__main__":
    main()
