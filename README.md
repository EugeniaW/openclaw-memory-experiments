# OpenClaw Memory Pilot Experiments

This repo contains a minimal, checkable pilot pipeline for hand-curated fixtures stored under `data/fixtures`.

Current outputs:

- `reports/pilot_summary.csv`
- `reports/pilot_report.md`

Scripts:

- `scripts/load_fixtures.py` discovers fixture directories and reads the expected files.
- `scripts/build_pilot_summary.py` normalizes observable fields and writes the report artifacts.

Run:

```bash
python3 scripts/build_pilot_summary.py
```

The pipeline reports only direct observations from the fixture files. It does not fabricate missing run content or claim experimental findings.
