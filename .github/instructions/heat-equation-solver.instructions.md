---
description: "Use when writing, extending, or reviewing code that solves the 2D heat equation with boundary conditions — grid setup, finite-difference discretization, Dirichlet/Neumann/Robin BCs, steady-state and transient solvers, verification, and visualization."
applyTo: "**/*.py"
---
# 2D Heat Equation Solver

Governing equation: $\partial_t u = \alpha\,(\partial_{xx} u + \partial_{yy} u) + q$, on a rectangular domain with a structured grid. Steady state drops the time term to the Poisson/Laplace form $\alpha\,\nabla^2 u + q = 0$.

## Stack

- Python, managed with `uv` (`uv add`, `uv pip install`) — never bare `pip`.
- NumPy for arrays and vectorized math; SciPy for sparse linear algebra (`scipy.sparse`, `scipy.sparse.linalg.spsolve`) and sparse assembly.
- Matplotlib for plots.

## Discretization

- Structured grid with spacing `dx`, `dy`; index fields as `u[i, j]` where `i` = row (y), `j` = column (x). State this convention in docstrings.
- Second-order central differences for the Laplacian.
- Assemble the operator as a **sparse** matrix (`scipy.sparse.lil_matrix` for building, convert to `csr_matrix` before solving). Never build a dense `N×N` system for a grid.
- Vectorize with NumPy slicing/`np.roll`-style stencils. No nested Python loops over grid points in hot paths.

## Boundary conditions

Support all three, selectable per edge:
- **Dirichlet** (fixed temperature): set the node value; remove its unknown or pin the row.
- **Neumann** (fixed flux / insulated `∂u/∂n = 0`): use ghost nodes or one-sided second-order stencils; do not silently reduce to first order.
- **Robin** (convective `-k ∂u/∂n = h(u - u∞)`): fold `h`, `u∞` into the boundary row.

Validate that every edge has exactly one BC specified before assembling. Raise a clear error otherwise.

## Solvers

- **Steady state**: assemble sparse `A u = b`, solve with `scipy.sparse.linalg.spsolve`.
- **Transient**: offer explicit (forward Euler) and implicit (backward Euler / Crank–Nicolson).
  - For explicit, check the stability limit $\Delta t \le \frac{1}{2\alpha}\left(\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}\right)^{-1}$ and warn or clamp if violated.
  - Prefer implicit for stiff or large `Δt` cases.

## Interface

- Keep the solver a pure function/class: inputs = grid, material props (`alpha`, `k`), source term, BC spec; output = solution field plus grid coordinates. No hidden globals.
- Make grid size, BCs, material properties, and time stepping configurable inputs (function args or a small config object), not hardcoded constants.
- Return NumPy arrays; keep plotting and I/O out of the numerical core.

## Verification

- Add at least one test against a known analytical solution (e.g., steady state with Dirichlet edges, or 1D-reducible cases) and assert the max/L2 error decreases under grid refinement (order-of-accuracy check).
- Sanity-check conservation/steady-state residuals; report the residual norm.

## Visualization

- 2D temperature field: `plt.contourf` or `imshow` with a labeled colorbar (units), correct `extent`, and equal aspect for physical geometry.
- Label axes with physical coordinates, not indices.
- Don't hand-roll plotting — reuse the `heat-plots` skill helper ([plot_field.py](../skills/heat-plots/scripts/plot_field.py)): `plot_field`, `plot_profile`, `plot_comparison`, `save`. It already encodes these conventions.

## Project tooling

This repo ships a grounded workflow around the solver. Prefer these over ad-hoc work:

- **Ground the physics first.** Get the governing equation, boundary conditions, and properties from the textbook RAG before coding, and cite them: `uv run python -m heat_rag ask "<query>"` (raw passages) or `answer` (synthesized, cited). See the [heat-transfer-rag skill](../skills/heat-transfer-rag/SKILL.md). Put a `# cite: <book>, p. <printed> (PDF p. <pdf>)[, eq. <label>]` comment on every physics term; numerical-method lines (stencil, assembly, time-stepping) stay uncited.
- **Agents** (pick the right one; they don't overlap):
  - *Heat Solver Builder* — breaks a problem down, grounds it via RAG, and writes the cited solver. Entry point: the [/solve-heat-case prompt](../prompts/solve-heat-case.prompt.md).
  - *Solver Reviewer* — read-only audit of existing solver code against this file and the textbook.
  - *Result Interpreter* — read-only physical sanity-check of results against textbook correlations.
- **Plots**: the [heat-plots skill](../skills/heat-plots/SKILL.md).
