# Journal.md

## Purpose

Use this file to record concise, iterative notes about efforts related to building the portfolio-management system, the simulation, and the supporting environment/data layer.

Keep each entry short and practical.

## Entry Format

For each new entry, append:

### YYYY-MM-DD - Short Title

- What did we try and why? Briefly describe the change, experiment, or decision and the reason for it.
- What was the result? State the outcome, including whether it worked, partially worked, or failed.
- What should we do next? Record the next concrete step.

## Example

### 2026-04-10 - Initial Journal Setup

- What did we try and why? Created a shared journal format so agents can leave a compact record of implementation and simulation work.
- What was the result? The repository now has a standard structure for short iterative logs.
- What should we do next? Start appending entries whenever we test, change, or evaluate a meaningful part of the system.

### 2026-04-11 - Simplified Baseline Workflow

- What did we try and why? Replaced the earlier single-ticker prototype path with a simpler baseline workflow built around prepared Supabase daily packages, explicit screening steps, one shared deep-analysis set, one portfolio-manager decision, and one deterministic rebalance preview. The goal was to make the architecture easier to understand for business students and closer to the artifact specification.
- What was the result? The baseline now auto-resolves the latest prepared package date, loads 30 screening rows per analyst from Supabase, initializes portfolio state from cash when no prior run exists, and produces a shared deep-analysis set through explicit screening logic. Local tests passed (`16/16`), the package-loading smoke test succeeded on `2026-04-09`, and a model ping returned `baseline-ok`.
- What should we do next? Run the full workflow interactively, inspect the first stored portfolio decision in Supabase, and then decide which older experimental modules can be archived because they are no longer on the baseline path.

### 2026-04-11 - Parallel Analyst Layers

- What did we try and why? Changed the baseline graph so the three screening nodes run in parallel from the same loaded package state, and the three deep-analysis nodes also run in parallel after the shared deep-analysis set is built. This matches the artifact-spec logic more closely while keeping the workflow simple.
- What was the result? The architecture is still explicit, but the specialist analyst stages no longer form an unnecessary sequential chain. The merge points remain easy to explain: all screening outputs meet before the shared set is built, and all deep-analysis reports meet before the Portfolio Manager acts.
- What should we do next? Re-run the baseline tests and one smoke import to confirm the graph still compiles cleanly with the parallel fan-out and fan-in edges.
