# Phase 1 — Team Management Computational Simulation

This folder contains versioned computational simulations for the
Phase 1 synergy-learning task. Each version lives in its own
self-contained folder with its own `simulate.py` and `outputs/`.

## Versions

- `v01_minimal/` — deterministic argmax agent, fixed learning rate.
  Validates the basic loop: synergy belief -> outcome prediction ->
  choice -> feedback -> synergy inference -> belief update.

## Conventions

- Each version defines a single `VERSION` string constant that
  controls all output filenames (e.g. `outputs/results/v01_simulation_results.csv`).
- `S_true` (true synergy) belongs only to the environment and must
  never be used by the agent to predict outcomes or make choices.
- Outputs are written to `outputs/figures/` and `outputs/results/`
  within each version's folder, created automatically via `pathlib`.
