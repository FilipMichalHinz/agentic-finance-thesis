# AGENTS.md

## Purpose

This repository exists to build an agentic portfolio management system, along with the simulation, environment, and data layer it interacts with.

Later branches may explore resilience mechanisms in the architecture. This branch should optimize for a clear, working baseline, not for speculative future complexity.

## Core Principles

- Do not overengineer.
- Always choose the simplest solution that satisfies the current requirement.
- Do not optimize for hypothetical future complexity without a concrete signal from current requirements.
- If two solutions work, prefer the one with fewer moving parts, less indirection, and lower maintenance cost.
- Favor clear, explicit code over clever abstractions.
- Make the smallest change that fully solves the problem.

## Scope Guidance

- Focus current work on the portfolio management agents, the simulation loop/environment, and the data those components need.
- Treat resilience features as future-branch work unless the current task explicitly requires them.
- Avoid introducing extension points, abstractions, or infrastructure "for later" unless there is a concrete, present need.

## Coding Expectations

- Keep code simple, readable, and easy to reason about.
- Prefer straightforward control flow over generic or highly abstract patterns.
- Keep functions and modules focused on one job.
- Minimize dependencies and layers unless they clearly simplify the current implementation.
- Use comments and docstrings to explain intent, assumptions, constraints, and non-obvious behavior.
- Write comments to help the next person understand why the code exists or why a decision was made, not to restate obvious syntax.

## Decision Rule

Before adding complexity, ask:

1. Does this solve a real problem in the current portfolio-management workflow?
2. Is this the simplest implementation that would work today?
3. Am I adding this because it is needed now, or because it might be useful later?

If the answer to the third question is "later," do not add it yet.
