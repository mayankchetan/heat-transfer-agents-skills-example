---
description: "Set up and solve a heat-transfer problem in Python, grounded in the textbook RAG with page/equation citations on every physics term. Fill in the problem template, then hand off to the Heat Solver Builder agent."
name: "Solve Heat Case"
agent: "Heat Solver Builder"
argument-hint: "geometry + conditions, or fill the template below"
---
Set up and solve the heat-transfer problem described below, following the
[Heat Solver Builder](../agents/heat-solver-builder.agent.md) workflow and the
[finite-difference conventions](../instructions/heat-equation-solver.instructions.md).

## Problem
${input:describe the problem, or fill the fields below}

Fill any of these that apply (leave blank if unknown — ask me one question if a
required field is missing):

- **Geometry / domain**: (e.g. 1 m × 1 m plate; L-shaped region)
- **Dimensionality**: 1D / 2D
- **Regime**: steady-state / transient (give final time + Δt if transient)
- **Material**: (name or values for k, α; note the source if you have one)
- **Internal source** q: (0, constant, or a function of position)
- **Boundary conditions** (one per edge):
  - left:
  - right:
  - top:
  - bottom:
- **Find**: (temperature field, heat flux, max temperature, ...)

## Requirements
1. Break the problem down, then ground the governing equation, each boundary
   condition, and each material property via the RAG
   (`uv run python -m heat_rag ask "..."` / `answer`). Show the cited setup before
   coding.
2. Implement in Python per the instruction file. Put a
   `# cite: ...` comment on every **physics** term (PDE, BC rows, k/α/h, source).
   Numerical-method lines (stencil, sparse assembly, time-stepping) stay uncited.
3. Verify: analytical comparison if a closed form exists, else report the residual
   norm. Run it — do not report success on unrun code.
4. End with a **Sources** list of every page/equation cited, and flag any term the
   RAG could not support.
