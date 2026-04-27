# OpenClaw Memory Research Plan

> **Goal:** Understand where and why LLM memory systems fail in real agent workflows — focusing on the gap between *remembering* facts and *using* them in decisions — and generalize findings to any LLM harness layer.

## Table of Contents

- [Motivation](#motivation)
- [Phase 0: Pilot Study (Completed)](#phase-0-pilot-study-completed)
- [Phase 1: Infrastructure & Repo Cleanup](#phase-1-infrastructure--repo-cleanup)
- [Phase 2: Scale & Harden](#phase-2-scale--harden)
- [Phase 3: Real OpenClaw Integration](#phase-3-real-openclaw-integration)
- [Phase 4: Intervention Experiments](#phase-4-intervention-experiments)
- [Phase 5: Root Cause Analysis & Fix](#phase-5-root-cause-analysis--fix)
- [Generalization to LLM Harness Layers](#generalization-to-llm-harness-layers)
- [Quality Framework](#quality-framework)
- [Timeline](#timeline)

---

## Motivation

LLM-based agents increasingly rely on external memory systems (file-based notes, vector stores, structured databases) to maintain continuity across sessions. A critical but under-studied failure mode is **application failure**: the agent can *recall* a fact when asked directly, but fails to *apply* it when making a decision that depends on that fact.

This distinction matters because most memory evaluations test recall ("What is X?") rather than downstream utility ("Given everything you know, should we do Y?"). An agent that scores 100% on recall but 17% on decision use is functionally broken for real-world tasks — yet would appear healthy under standard evaluations.

This research aims to:

1. **Quantify** the recall–application gap across models, memory architectures, and context conditions
2. **Diagnose** root causes (retrieval ranking? attention decay? instruction following? prompt position?)
3. **Fix** the failures at the harness layer, with regression-tested improvements
4. **Generalize** findings beyond OpenClaw to any system that injects recalled facts into LLM context

---

## Phase 0: Pilot Study (Completed)

### Design

The **Temporal Update Decision-Utility Probe** tests whether an agent uses *updated* facts in downstream decisions. Each scenario follows a three-step structure:

1. **Initial fact** — e.g., "Your favorite restaurant is Sakura Sushi"
2. **Updated fact** — e.g., "Sakura Sushi closed permanently last week"
3. **Decision prompt** — e.g., "Where should we go for dinner tonight?"

The agent is scored on two dimensions:

| Metric | Definition |
|--------|-----------|
| `latest_fact_fidelity` | Does the agent recall the updated fact when asked directly? |
| `decision_use_rate` | Does the agent's decision reflect the updated fact? |

### Results (6 scenarios)

| Metric | Value |
|--------|-------|
| `latest_fact_fidelity` | **1.000** (6/6) |
| `decision_use_rate` | **0.167** (1/6) |
| Application failure rate | **83.3%** (5/6) |

**Key finding:** Perfect recall, near-zero decision use. The model *knows* the updated fact but doesn't *use* it when making a choice.

### Limitations

- **CLI mode only** — scenarios run via direct prompting, not through OpenClaw's actual memory system
- **Phrase-match scoring** — brittle; misses semantically correct but differently-worded responses
- **No control group** — cannot distinguish "memory system problem" from "LLM reasoning problem"
- **Small scale** — 6 scenarios, single model, single trial per scenario

---

## Phase 1: Infrastructure & Repo Cleanup

**Duration:** 1 week

### Objective

Establish a clean, reproducible evaluation infrastructure that supports multi-model, multi-trial experiments with automated scoring and baseline tracking.

### Target Repository Layout

```
openclaw-memory-eval/
├── benchmarks/
│   └── temporal_update/
│       └── scenarios.json          # All scenario definitions
├── runners/
│   ├── run_cli.py                  # Direct LLM prompting (current mode)
│   └── run_openclaw.py             # OpenClaw session-based runner (Phase 3)
├── scorers/
│   ├── phrase_scorer.py            # Legacy phrase-match scorer
│   └── llm_judge_scorer.py         # LLM-as-judge scorer (Phase 2)
├── eval/
│   └── temporal_update/
│       ├── results.csv             # Latest run results
│       ├── baseline.csv            # Reference baseline for regression
│       └── charts/                 # Auto-generated visualizations
├── scripts/
│   ├── plot.py                     # Visualization generation
│   └── diff_baseline.py           # Baseline comparison tool
└── docs/
    ├── RESEARCH_PLAN.md            # This document
    └── findings/                   # Per-phase writeups
```

### Deliverables

- [ ] Restructure repo to target layout
- [ ] Add `trial_id` and `seed` to every run for reproducibility
- [ ] Standardize log paths: `eval/{benchmark}/{model}/{trial_id}/`
- [ ] Implement `diff_baseline.py` — compares current results against `baseline.csv`, flags regressions
- [ ] CI check: `pytest` runs phrase scorer on a known-answer scenario to verify tooling isn't broken

---

## Phase 2: Scale & Harden

**Duration:** 2 weeks

### Objective

Expand from a 6-scenario pilot to a robust benchmark with 30+ scenarios, upgraded scoring, and multi-model coverage.

### Scenario Expansion (6 → 30+)

**Generation process:**

1. Use an LLM to draft candidate scenarios across diverse domains (medical, financial, travel, scheduling, personal preferences, safety-critical)
2. Human review every scenario against the **Scenario Review Checklist** (see below)
3. Tag each scenario with metadata: `domain`, `stakes` (low/medium/high), `update_type` (contradiction/refinement/retraction)

**Scenario Review Checklist** (inspired by QF-Bench):

- [ ] **Oracle ground truth** — there is exactly one correct decision given the updated fact
- [ ] **Clear pass/fail** — the expected decision implication is unambiguous
- [ ] **No shortcut** — the correct decision cannot be reached without knowing the updated fact
- [ ] **Realistic** — the scenario reflects a plausible real-world situation
- [ ] **Diverse** — covers a domain/update-type not already saturated in the benchmark

### Scoring Upgrade

Replace brittle phrase matching with **LLM-as-judge**:

- Judge receives: scenario definition, expected decision implications, agent's actual response
- Judge outputs: `{recall_score: 0|1, decision_score: 0|1, reasoning: "..."}`
- Calibrate judge against human labels on the original 6 scenarios before deploying
- Track judge agreement rate and flag low-confidence judgments for human review

### Multi-Model Comparison

Run the full benchmark across:

| Model | Role |
|-------|------|
| Haiku 4.5 | Fast/cheap baseline |
| Sonnet 4.5 | Mid-tier |
| Opus 4.6 | Top-tier |

Each model × 3 trials minimum (to measure variance).

### Deliverables

- [ ] 30+ reviewed scenarios in `benchmarks/temporal_update/scenarios.json`
- [ ] LLM-as-judge scorer with calibration data
- [ ] Multi-model results matrix
- [ ] Findings writeup: `docs/findings/phase2_scale.md`

---

## Phase 3: Real OpenClaw Integration

**Duration:** 2–3 weeks

### Objective

Move from synthetic CLI prompting to running scenarios through OpenClaw's actual memory system, with controlled experimental conditions that isolate whether failures come from the memory layer or the underlying LLM.

### Runner Design (`run_openclaw.py`)

For each scenario:

1. **Create session** — start a fresh OpenClaw agent session
2. **Inject initial facts** — write them into the session's `MEMORY.md`
3. **Send update** — deliver the updated fact as a new user message (agent processes and may update memory)
4. **Decision prompt** — send the decision question
5. **Extract trace** — capture `memory_read`/`memory_write` operations from the session transcript
6. **Score** — run LLM-as-judge on the decision output

### Experimental Conditions

| Condition | Memory System | Context Setup | Purpose |
|-----------|--------------|---------------|---------|
| **A: memory-on** | OpenClaw normal | Facts in MEMORY.md, update via message | Test the real system |
| **B: memory-off** | Disabled | All facts (initial + update) in prompt only | Isolate LLM reasoning ability |
| **C: oracle** | N/A | Latest facts injected into system prompt | Upper bound on performance |

**Interpretation matrix:**

| A (memory-on) | B (memory-off) | C (oracle) | Diagnosis |
|:-:|:-:|:-:|-----------|
| ✗ | ✗ | ✗ | LLM fundamentally can't do this task |
| ✗ | ✗ | ✓ | Prompt position/format matters |
| ✗ | ✓ | ✓ | Memory retrieval/injection is the problem |
| ✓ | ✗ | ✓ | Memory system helps (surprising!) |
| ✓ | ✓ | ✓ | Everything works |

### Deliverables

- [ ] `run_openclaw.py` with full trace capture
- [ ] Results for conditions A/B/C across all scenarios and models
- [ ] Diagnosis per scenario: memory problem vs. LLM problem
- [ ] Findings writeup: `docs/findings/phase3_openclaw.md`

---

## Phase 4: Intervention Experiments

**Duration:** 2 weeks

### Objective

Test specific hypotheses about *why* application failure occurs and *what harness-level changes* could fix it.

### Experiment 1: Memory Position

Place the updated fact at different positions in the context window:

| Position | Description |
|----------|------------|
| Beginning | Updated fact near the start of context |
| Middle | Updated fact buried in the middle |
| End | Updated fact near the decision prompt |

**Hypothesis:** Recency bias means end-position will outperform beginning/middle.

### Experiment 2: Memory Format

Present the same facts in different formats:

| Format | Example |
|--------|---------|
| Natural language | "Note: Sakura Sushi closed permanently last week." |
| Structured JSON | `{"restaurant": "Sakura Sushi", "status": "permanently_closed", "updated": "2025-04-20"}` |
| Bullet points | `- ⚠️ UPDATED: Sakura Sushi → permanently closed (as of 2025-04-20)` |
| Instruction-wrapped | `[CRITICAL UPDATE — use this in all decisions] Sakura Sushi has closed.` |

**Hypothesis:** Instruction-wrapped format will show highest decision use rate.

### Experiment 3: Context Pressure

Vary the total context utilization to test how performance degrades under pressure:

| Zone | Context Utilization | Expected Behavior |
|------|-------------------|-------------------|
| Safe | 25% | Baseline performance |
| Normal | 50% | Minor degradation |
| Compression | 75% | Noticeable drop |
| Failure-Risk | 90% | Significant failure |

This maps to the **Zone concept** from the original research planning: identifying the context utilization threshold where memory application breaks down.

### Deliverables

- [ ] Position × Format × Pressure results matrix
- [ ] Identification of optimal injection strategy
- [ ] Findings writeup: `docs/findings/phase4_interventions.md`

---

## Phase 5: Root Cause Analysis & Fix

**Duration:** Ongoing

### Objective

Link decision-level failures to specific memory operations, build a failure taxonomy, and propose + test fixes in the OpenClaw memory layer.

### Failure Taxonomy

Refine the broad "application failure" category into granular sub-types:

| Sub-type | Description | Example |
|----------|------------|---------|
| **Retrieval miss** | Memory system didn't return the updated fact | `memory_read` results don't contain the update |
| **Retrieval ranking** | Updated fact returned but ranked low/buried | Update is item #15 in returned results |
| **Attention decay** | Fact is in context but model doesn't attend to it | Long context, update far from decision point |
| **Instruction gap** | Model sees the fact but doesn't recognize it as decision-relevant | No explicit link between fact and decision type |
| **Reasoning failure** | Model sees and recognizes the fact but reasons incorrectly | Acknowledges closure but still recommends the restaurant |

### Fix Development Process

For each identified failure sub-type:

1. **Characterize** — which scenarios trigger it, at what rate
2. **Hypothesize** — what harness-level change could fix it
3. **Implement** — modify OpenClaw's memory layer
4. **Test** — re-run the full benchmark
5. **Regress** — verify no degradation on previously-passing scenarios

### Deliverables

- [ ] Failure taxonomy with per-scenario attribution
- [ ] At least 2 proposed fixes, tested and regression-checked
- [ ] Regression dashboard tracking fix effectiveness over time

---

## Generalization to LLM Harness Layers

### Objective

Abstract findings from OpenClaw-specific experiments into general principles applicable to any system that manages LLM memory.

### Key Research Questions

1. **Injection strategy** — How should a harness layer present recalled facts to the LLM? (Position, format, salience markers)
2. **Update propagation** — When a fact changes, how should the harness ensure the LLM treats the new version as authoritative?
3. **Decision-awareness** — Should the harness analyze the current query and force-surface facts likely relevant to the decision, rather than relying on generic retrieval?
4. **Context budgeting** — Given a context window budget, how should the harness allocate space between instructions, recalled facts, conversation history, and the current query?

### Planned Output

- Technical report documenting the recall–application gap phenomenon, its causes, and harness-level mitigations
- Open-source benchmark and evaluation toolkit
- Recommendations for memory system designers

---

## Quality Framework

Inspired by the rigor of [QF-Bench](https://github.com/QF-Bench) benchmark review practices, this project adopts the following quality standards:

### Scenario Quality

| Standard | Requirement |
|----------|------------|
| **Machine-verifiable ground truth** | Every scenario has an unambiguous expected decision that can be checked programmatically |
| **Oracle answer** | A reference "perfect" answer exists for calibrating the judge |
| **No ambiguity** | The `expected_decision_implications` field admits exactly one correct interpretation |
| **Human-reviewed** | Every scenario passes the review checklist before inclusion |

### Experimental Rigor

| Standard | Requirement |
|----------|------------|
| **Multi-model** | Every claim is tested across ≥3 models |
| **Multi-trial** | Every (model, scenario) pair runs ≥3 trials with different seeds |
| **Automated** | Full pipeline runs without manual intervention |
| **Reproducible** | Trial ID + seed + model version fully determines output |

### Regression & Tracking

| Standard | Requirement |
|----------|------------|
| **Baseline tracking** | `diff_baseline.py` catches regressions before merge |
| **Dashboard** | Automated charts track metrics across versions |
| **Granular attribution** | Failures are attributed to specific sub-types, not just pass/fail |
| **Benchmark self-review** | The benchmark itself is periodically audited for scenario quality drift |

---

## Timeline

| Phase | Duration | Key Deliverable | Success Criteria |
|-------|----------|----------------|-----------------|
| **0** (done) | — | 6-scenario pilot | Recall–application gap identified |
| **1** | 1 week | Clean repo, baseline tracking | `diff_baseline.py` runs in CI |
| **2** | 2 weeks | 30+ scenarios, LLM judge, multi-model | All scenarios pass review checklist; ≥3 models tested |
| **3** | 2–3 weeks | OpenClaw integration, control groups | Conditions A/B/C results for all scenarios |
| **4** | 2 weeks | Intervention experiments | Optimal injection strategy identified |
| **5** | Ongoing | Root cause analysis, fixes, regression | ≥2 fixes tested with regression tracking |

**Total estimated time to Phase 4 completion:** 7–8 weeks

---

## Contributing

This is a collaborative project between the OpenClaw team. To contribute:

1. Fork the repo and create a feature branch
2. Follow the scenario review checklist for new scenarios
3. Run the full evaluation pipeline before submitting a PR
4. Include a findings summary for any new experimental results

---

*Last updated: 2025-04-27*
