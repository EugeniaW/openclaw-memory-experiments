# Pilot Fixture Report

## Scope

This report summarizes the pilot fixtures currently present under `data/fixtures`.
It reports only directly observable fixture properties such as file presence and content length.
It does not infer run behavior, memory quality, or experimental findings beyond the available files.

## Fixtures Present

- Fixture directories found: 3
- Runs with all expected files present: 3
- Runs with non-empty task and output files: 0
- Runs with any non-empty file content: 0

| run_id | task | output | notes | task chars | output chars | notes chars | minimally complete |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| run-20260415-001 | True | True | True | 0 | 0 | 0 | False |
| run-20260415-002 | True | True | True | 0 | 0 | 0 | False |
| run-20260415-003 | True | True | True | 0 | 0 | 0 | False |

## What Is Missing

- `run-20260415-001`: empty task_prompt.md, empty final_output.md, empty notes.md
- `run-20260415-002`: empty task_prompt.md, empty final_output.md, empty notes.md
- `run-20260415-003`: empty task_prompt.md, empty final_output.md, empty notes.md

## What A Full Memory Experiment Would Need Next

- More non-empty pilot fixtures with preserved task prompts, outputs, and notes for each run.
- A stable fixture schema or manifest that records run metadata explicitly rather than inferring from directory names.
- Clear evaluation fields for memory-specific observations that can be checked without inventing missing run details.
- A documented procedure for syncing or copying approved fixtures from the separate dataset repo into this repo.
- Additional validation and reporting once real run content exists in the pilot fixtures.

## Traceability

- Source fixtures: `data/fixtures`
- CSV summary: `reports/pilot_summary.csv`
- Generated from observable file presence and lengths only.
