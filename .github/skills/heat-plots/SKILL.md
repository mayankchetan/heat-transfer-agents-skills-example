---
name: heat-plots
description: 'Create publication-quality plots of heat-solver results — 2D temperature fields (contour/heatmap), 1D line-outs/profiles, and numeric-vs-analytical comparisons with an error panel. Use when the user wants to plot, visualize, or figure a temperature field, heat map, isotherms, a temperature profile, or a solver-vs-exact comparison. Wraps a matplotlib helper that follows the repo visualization conventions (labeled colorbar with units, physical axes, equal aspect).'
argument-hint: 'what to plot (field / profile / comparison) and where the arrays come from'
---

# Heat-Result Plots

Turn solver output into clear figures. The numerical core returns NumPy arrays; this
skill only visualizes them, keeping plotting out of the solver (per
`.github/instructions/heat-equation-solver.instructions.md`). All helpers live in
[plot_field.py](./scripts/plot_field.py).

## When to Use
- "Plot the temperature field / heat map / isotherms."
- "Show a temperature profile along a line (a line-out)."
- "Compare my numerical solution to the analytical one and show the error."

## Data Contract
Every helper takes physical coordinates plus the field:
- `x`: 1D array of column (x) coordinates, length `nx`.
- `y`: 1D array of row (y) coordinates, length `ny`.
- `T`: 2D array shaped `(ny, nx)`, indexed `T[i, j]` (row = y, col = x) — the repo
  convention. Values in kelvin (or state the unit).

## Procedure
1. Obtain `x, y, T` from the solver (arguments, a `.npz`, or by running the case).
2. Import the helper and call the function that matches the goal:
   - `plot_field(x, y, T)` → filled contour / heatmap of the 2D field.
   - `plot_profile(coord, T_line, xlabel=...)` → 1D line-out.
   - `plot_comparison(x, y, T_num, T_exact)` → numeric, exact, and error panels.
3. Save with `save(fig, "figures/<name>.png")` (creates `figures/` if needed).
4. Describe what the figure shows; if verifying, quote the max error the comparison
   panel reports.

## Conventions (enforced by the helper)
- Colorbar always labeled with units; axes labeled with physical coordinates.
- `imshow(origin="lower")` with correct `extent`, `aspect="equal"` for true geometry.
- Perceptually-uniform colormap (`inferno` for fields, `coolwarm` for error).
- Never plot against grid indices; always against `x`/`y`.

## Example
```python
import numpy as np
from heat_plots import plot_field, plot_comparison, save  # scripts/plot_field.py

x = np.linspace(0.0, 1.0, nx)      # column (x) coordinates
y = np.linspace(0.0, 1.0, ny)      # row (y) coordinates
fig = plot_field(x, y, T, title="Steady conduction")   # T shaped (ny, nx)
save(fig, "figures/steady_field.png")
```
Quick styling check without any solver output:
```bash
uv run python .github/skills/heat-plots/scripts/plot_field.py --demo
```
The `--demo` flag renders a sample field to `figures/` so you can confirm the styling
before wiring in real solver output.
