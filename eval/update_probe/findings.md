# Temporal Update + Decision Utility Probe Findings

## Experiment Goal

This probe evaluates whether the system can use the latest updated business facts in final decision-making, rather than relying on stale or superseded facts.

The experiment is designed to move beyond simple recall testing. It focuses on decision utility: whether updated facts actually affect the final recommendation, rejected options, risks, and action plan.

## Setup

The benchmark includes 6 scenarios:

- 2 GTM constraint update scenarios
- 2 ICP / buyer-chain update scenarios
- 2 competitor / market-signal update scenarios

Each scenario contains:

- initial facts
- later updates that supersede some initial facts
- distractor information
- expected latest facts
- expected decision implications

The model was run through CLI mode, and raw outputs were saved under:

- `eval/update_probe/raw/`

The scoring pipeline generated:

- `eval/update_probe/results.csv`
- `eval/update_probe/summary.md`
- `eval/update_probe/latest_fact_fidelity.png`
- `eval/update_probe/failure_breakdown.png`

## Metrics

The probe tracks five main metrics:

1. `latest_fact_fidelity`  
   Whether the final answer uses the latest updated facts.

2. `stale_fact_usage`  
   Whether the final answer still relies on superseded facts.

3. `decision_use_rate`  
   Whether the updated facts actually affect the final recommendation.

4. `contradiction_count`  
   Whether old and new facts are used together in a conflicting way.

5. `update_sensitivity`  
   Whether the final strategic recommendation changes in response to the updated facts.

## Mapping to Memory Failure Types

- Low latest-fact fidelity suggests storage or update-tracking failure.
- Good recall but low decision use suggests application failure.
- Stale or contradictory usage suggests consistency failure.

## Preliminary Interpretation

This probe provides a first code-based way to evaluate OpenClaw memory beyond recall. The key question is not only whether facts can be remembered, but whether updated facts are used correctly in final decisions.

At this stage, the experiment should be treated as a pilot result. It provides a reproducible benchmark structure, raw outputs, scoring results, and visualization artifacts, but should be expanded with more scenarios and direct OpenClaw session traces in the next iteration.

## Next Step

The next step is to connect this probe to full OpenClaw runtime logs, including step-level traces, tool calls, memory reads, memory writes, and injected memory content. That will allow the current decision-level metrics to be linked back to concrete memory operations.
