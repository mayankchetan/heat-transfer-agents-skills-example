"""Steady-state 2D heat conduction on an equilateral triangle (finite differences).

Physics (all grounded in *A Heat Transfer Textbook*, 6th ed., Lienhard & Lienhard):
governing Laplace equation, Dirichlet (1st-kind) and convective Robin (3rd-kind)
boundary conditions, and Fourier's law for the flux. Numerical method (structured
grid, masked staircase boundary, sparse central-difference operator, ghost-node
Robin row, direct sparse solve) follows the repo conventions in
`.github/instructions/heat-equation-solver.instructions.md` and carries no citation.

Geometry: equilateral triangle, side L, base on the x-axis (y = 0) from x = 0 to
x = L, apex at (L/2, L*sqrt(3)/2). The base is the convective heat sink; the two
slanted edges are held at fixed temperatures.

Index convention: fields are shaped (ny, nx) and indexed T[i, j] with i = row (y,
bottom-up) and j = column (x). Nodes outside the triangle are NaN.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve

# --- Material and boundary data (physics; cited) --------------------------------
# cite: A Heat Transfer Textbook, 6th ed. (Lienhard & Lienhard, 2024), p. 740
#       (PDF p. 754), Table A.1 -- AISI 304 stainless steel, k ~ 13.8 W/m.K at 20 C.
K_METAL = 14.0          # W/(m.K)  thermal conductivity of AISI 304 stainless steel
T_HOT = 100.0           # deg C, left slanted edge (Dirichlet, 1st kind)
T_COLD = 27.0           # deg C, right slanted edge (Dirichlet, 1st kind)
T_INF = 27.0            # deg C, convective sink free-stream temperature
# h is a design choice (not a textbook property): set so Bi = h*L/k is order 1-3,
# making the convective sink physically visible. With L = 0.1 m and k = 14 W/m.K,
# h = 280 gives Bi = 2.0.  For steady conduction with these BCs the field shape
# depends on the Biot number Bi = h*L/k.
H_CONV = 280.0          # W/(m^2.K), convection coefficient at the base sink


@dataclass
class TriangleSolution:
    """Solver output: temperature field and grid, plus reporting metadata."""

    x: np.ndarray           # column (x) coordinates, length nx
    y: np.ndarray           # row (y) coordinates, length ny
    T: np.ndarray           # (ny, nx) field, deg C, NaN outside the triangle
    inside: np.ndarray      # (ny, nx) bool mask of active (inside-triangle) nodes
    residual: float         # ||A u - b||_2 of the solved linear system
    dx: float
    dy: float
    k: float                # thermal conductivity used in the solve, W/(m.K)


def _classify(nx: int, ny: int, x: np.ndarray, y: np.ndarray, L: float):
    """Return masks: inside, base (Robin), left/right slant (Dirichlet), interior."""
    xx, yy = np.meshgrid(x, y)                       # (ny, nx)
    tol = 1e-9
    # Interior of the equilateral triangle: above the base, below both slant lines.
    # Left slant line  y = sqrt(3) x        -> inside where y <= sqrt(3) x
    # Right slant line y = sqrt(3) (L - x)  -> inside where y <= sqrt(3) (L - x)
    inside = (
        (yy >= -tol)
        & (yy <= np.sqrt(3.0) * xx + tol)
        & (yy <= np.sqrt(3.0) * (L - xx) + tol)
    )

    # An active node touching an inactive/off-grid neighbour lies on a slant edge.
    def _shift(mask, di, dj):
        out = np.zeros_like(mask)
        sl_i_dst = slice(max(di, 0), ny + min(di, 0))
        sl_j_dst = slice(max(dj, 0), nx + min(dj, 0))
        sl_i_src = slice(max(-di, 0), ny + min(-di, 0))
        sl_j_src = slice(max(-dj, 0), nx + min(-dj, 0))
        out[sl_i_dst, sl_j_dst] = mask[sl_i_src, sl_j_src]
        return out

    left_act = _shift(inside, 0, -1)      # neighbour to the left is active
    right_act = _shift(inside, 0, +1)
    up_act = _shift(inside, +1, 0)
    has_dead_nbr = inside & ~(left_act & right_act & up_act)

    base = inside & (np.arange(ny)[:, None] == 0)     # bottom row y = 0 -> Robin
    slant = has_dead_nbr & ~base                      # slanted edges -> Dirichlet
    # Split slant nodes by side of the apex; base end nodes handled as corners.
    left_edge = slant & (xx < L / 2.0)
    right_edge = slant & (xx >= L / 2.0)
    return inside, base, left_edge, right_edge


def solve_triangle(
    L: float = 0.1,
    n_base: int = 200,
    *,
    k: float = K_METAL,
    h: float = H_CONV,
    t_hot: float = T_HOT,
    t_cold: float = T_COLD,
    t_inf: float = T_INF,
) -> TriangleSolution:
    """Solve steady conduction on the triangle. n_base = nodes across the base."""
    height = L * np.sqrt(3.0) / 2.0
    x = np.linspace(0.0, L, n_base)
    dx = x[1] - x[0]
    dy = dx                                   # near-square cells
    ny = int(round(height / dy)) + 1
    y = np.arange(ny) * dy
    nx = n_base

    inside, base, left_edge, right_edge = _classify(nx, ny, x, y, L)

    # Global unknown numbering over active nodes only (no dense N x N system).
    idx = -np.ones((ny, nx), dtype=int)
    active_ij = np.argwhere(inside)
    idx[inside] = np.arange(active_ij.shape[0])
    n_unknown = active_ij.shape[0]

    A = sp.lil_matrix((n_unknown, n_unknown))
    b = np.zeros(n_unknown)

    inv_dx2 = 1.0 / dx**2
    inv_dy2 = 1.0 / dy**2

    for i, j in active_ij:
        p = idx[i, j]
        is_base_end = base[i, j] and (j == 0 or j == nx - 1 or not inside[i, j + 1]
                                      or not inside[i, j - 1])

        if left_edge[i, j] or (base[i, j] and j == 0):
            # cite: p. 142 (PDF p. 156) -- b.c. of the first kind (fixed surface T).
            A[p, p] = 1.0
            b[p] = t_hot            # left slanted edge held hot
        elif right_edge[i, j] or (base[i, j] and j == nx - 1):
            # cite: p. 142 (PDF p. 156) -- b.c. of the first kind (fixed surface T).
            A[p, p] = 1.0
            b[p] = t_cold           # right slanted edge held at room temperature
        elif base[i, j] and not is_base_end:
            # Convective Robin (3rd-kind) base with a ghost node below y = 0.
            # cite: p. 142 (PDF p. 156) -- b.c. of the third kind,
            #       -k dT/dn = h (T - T_inf); with Newton's law of cooling
            # cite: p. 19 (PDF p. 33), eq. 1.17 -- q = h (T - T_inf).
            # Outward normal at the base points in -y, so k dT/dy = h (T - T_inf).
            # Ghost: T[-1] = T[1] - (2 dy h / k)(T[0] - T_inf), substituted below.
            A[p, p] += -2.0 * inv_dx2 - 2.0 * inv_dy2 - (2.0 * dy * h / k) * inv_dy2
            A[p, idx[i, j - 1]] += inv_dx2
            A[p, idx[i, j + 1]] += inv_dx2
            A[p, idx[i + 1, j]] += 2.0 * inv_dy2
            b[p] += -(2.0 * dy * h / k) * inv_dy2 * t_inf
        else:
            # Interior node: second-order central-difference Laplacian = 0.
            # cite: p. 56 (PDF p. 70), eq. 2.11 & 2.12 -- steady, source-free heat
            #       conduction equation reduces to the Laplace form del^2 T = 0.
            A[p, p] += -2.0 * inv_dx2 - 2.0 * inv_dy2
            for ii, jj, w in (
                (i, j - 1, inv_dx2), (i, j + 1, inv_dx2),
                (i - 1, j, inv_dy2), (i + 1, j, inv_dy2),
            ):
                q = idx[ii, jj]
                if q >= 0:
                    A[p, q] += w
                else:
                    # Fallback: a stray dead neighbour -> treat as nearest edge value.
                    b[p] += -w * (t_hot if jj < nx / 2 else t_cold)

    A = A.tocsr()
    u = spsolve(A, b)
    residual = float(np.linalg.norm(A @ u - b))

    T = np.full((ny, nx), np.nan)
    T[inside] = u
    return TriangleSolution(x=x, y=y, T=T, inside=inside, residual=residual,
                            dx=dx, dy=dy, k=k)


def _masked_grad(T: np.ndarray, d: float, axis: int) -> np.ndarray:
    """First derivative along ``axis`` with one-sided fallback at NaN neighbours.

    Uses a central difference where both neighbours are finite, otherwise falls
    back to a one-sided difference toward whichever neighbour is finite, and NaN
    only where the node is isolated. Numerical detail; carries no citation.
    """
    T = np.moveaxis(T, axis, 0)
    cen = np.full_like(T, np.nan)
    fwd = np.full_like(T, np.nan)
    bwd = np.full_like(T, np.nan)
    cen[1:-1] = (T[2:] - T[:-2]) / (2.0 * d)           # central (both neighbours)
    fwd[:-1] = (T[1:] - T[:-1]) / d                    # forward (+ neighbour)
    bwd[1:] = (T[1:] - T[:-1]) / d                     # backward (- neighbour)
    g = np.where(np.isfinite(cen), cen, fwd)
    g = np.where(np.isfinite(g), g, bwd)
    g = np.where(np.isfinite(T), g, np.nan)            # report only at active nodes
    return np.moveaxis(g, 0, axis)


def heat_flux(sol: TriangleSolution, k: float | None = None):
    """Fourier-law heat flux q = -k grad T (W/m^2), masked outside the triangle."""
    k = sol.k if k is None else k
    # cite: p. 51 (PDF p. 65), eq. 2.2 -- Fourier's law, q = -k grad T.
    T = np.where(sol.inside, sol.T, np.nan)
    dTdx = _masked_grad(T, sol.dx, axis=1)             # rows = y, cols = x
    dTdy = _masked_grad(T, sol.dy, axis=0)
    qx = -k * dTdx
    qy = -k * dTdy
    return qx, qy


def sink_heat_rate(sol: TriangleSolution, k: float | None = None) -> float:
    """Heat leaving through the convective base sink per metre depth (W/m).

    Integrate q.n over the *Robin* span of the base only (the two Dirichlet
    corner columns are excluded). The outward normal at the base is -y, so
    q.n = -q_y = k dT/dy|_{y=0}; a one-sided dT/dy keeps the derivative on the
    base, second order where a third interior row is available.
    """
    k = sol.k if k is None else k
    # cite: p. 51 (PDF p. 65), eq. 2.2 -- Fourier's law supplies q_y = -k dT/dy.
    robin = sol.inside[0] & sol.inside[1]              # base nodes with an interior
    j = np.where(robin)[0]                             #   neighbour above (Robin only)
    T0, T1, T2 = sol.T[0, j], sol.T[1, j], sol.T[2, j]
    second = np.isfinite(T2)                           # need a third row for O(dy^2)
    dTdy0 = np.where(second,
                     (-3.0 * T0 + 4.0 * T1 - T2) / (2.0 * sol.dy),
                     (T1 - T0) / sol.dy)               # into the domain (+y)
    qn = k * dTdy0                                     # W/m^2 leaving the base
    return float(np.trapezoid(qn, sol.x[j]))          # W per metre depth


def _solve_rect_manufactured(n: int, W: float = 1.0, k: float = 14.0,
                             h: float = 50.0):
    """Solve a square manufactured problem with the same interior + Robin machinery.

    Exact field T*(x, y) = sinh(pi y / W) sin(pi x / W) is harmonic, so it solves
    the source-free conduction equation exactly. Three edges take Dirichlet data
    from T*; the bottom edge (y = 0) is a convective Robin edge whose sink
    temperature T_inf(x) is manufactured to be consistent with T*. Returns the
    L2 and max errors of the discrete solution against T*.
    """
    x = np.linspace(0.0, W, n)
    y = np.linspace(0.0, W, n)
    dx = x[1] - x[0]
    dy = y[1] - y[0]
    xx, yy = np.meshgrid(x, y)                          # (n, n)
    Te = np.sinh(np.pi * yy / W) * np.sin(np.pi * xx / W)   # harmonic exact field
    idx = np.arange(n * n).reshape(n, n)

    A = sp.lil_matrix((n * n, n * n))
    b = np.zeros(n * n)
    inv_dx2 = 1.0 / dx**2
    inv_dy2 = 1.0 / dy**2

    for i in range(n):
        for j in range(n):
            p = idx[i, j]
            if i == n - 1 or j == 0 or j == n - 1:
                # cite: p. 142 (PDF p. 156) -- b.c. of the first kind (fixed T).
                A[p, p] = 1.0
                b[p] = Te[i, j]
            elif i == 0:
                # Convective Robin (3rd-kind) edge, ghost node below y = 0, with a
                # manufactured sink temperature T_inf(x) consistent with T*.
                # cite: p. 142 (PDF p. 156) -- b.c. of the third kind,
                #       -k dT/dn = h (T - T_inf).
                # cite: p. 51 (PDF p. 65), eq. 2.2 -- Fourier flux k dT/dy at y = 0.
                t_inf = Te[0, j] - (k / h) * (np.pi / W) * np.cosh(0.0) \
                    * np.sin(np.pi * x[j] / W)          # from k dT/dy = h(T - T_inf)
                A[p, p] += -2.0 * inv_dx2 - 2.0 * inv_dy2 - (2.0 * dy * h / k) * inv_dy2
                A[p, idx[i, j - 1]] += inv_dx2
                A[p, idx[i, j + 1]] += inv_dx2
                A[p, idx[i + 1, j]] += 2.0 * inv_dy2
                b[p] += -(2.0 * dy * h / k) * inv_dy2 * t_inf
            else:
                # cite: p. 56 (PDF p. 70), eq. 2.11 & 2.12 -- del^2 T = 0 interior.
                A[p, p] += -2.0 * inv_dx2 - 2.0 * inv_dy2
                A[p, idx[i, j - 1]] += inv_dx2
                A[p, idx[i, j + 1]] += inv_dx2
                A[p, idx[i - 1, j]] += inv_dy2
                A[p, idx[i + 1, j]] += inv_dy2

    u = spsolve(A.tocsr(), b)
    err = u.reshape(n, n) - Te
    l2 = float(np.sqrt(np.mean(err**2)))
    linf = float(np.max(np.abs(err)))
    return l2, linf


def verify() -> None:
    """Order-of-accuracy check for the interior Laplacian + one Robin edge.

    Solves the manufactured harmonic problem at two grids whose spacing halves and
    asserts the error drops and the observed order approaches 2 (second order).
    """
    n1, n2 = 41, 81                                     # dx ratio (n2-1)/(n1-1) = 2
    l2a, linfa = _solve_rect_manufactured(n1)
    l2b, linfb = _solve_rect_manufactured(n2)
    ratio = (n2 - 1) / (n1 - 1)
    order_l2 = np.log(l2a / l2b) / np.log(ratio)
    order_inf = np.log(linfa / linfb) / np.log(ratio)
    assert l2b < l2a and linfb < linfa, "error must decrease under refinement"
    assert order_l2 > 1.7, f"expected ~2nd order, got L2 order {order_l2:.2f}"
    print("-" * 64)
    print("Verification: manufactured harmonic field, interior + Robin edge")
    print(f"  grid {n1}^2 -> L2 err {l2a:.3e}, max err {linfa:.3e}")
    print(f"  grid {n2}^2 -> L2 err {l2b:.3e}, max err {linfb:.3e}")
    print(f"  observed order: L2 {order_l2:.2f}, max {order_inf:.2f}  (expect ~2)")


if __name__ == "__main__":
    from pathlib import Path
    import sys

    import matplotlib.pyplot as plt

    sys.path.insert(0, str(Path(__file__).parent / ".github/skills/heat-plots/scripts"))
    from plot_field import plot_field, save   # repo plotting helper

    L = 0.1
    sol = solve_triangle(L=L, n_base=200)
    Bi = H_CONV * L / K_METAL

    qx, qy = heat_flux(sol)
    q_sink = sink_heat_rate(sol)
    tmin = float(np.nanmin(sol.T))
    tmax = float(np.nanmax(sol.T))

    # --- Grid-refinement verification: sink heat rate should converge -----------
    coarse = solve_triangle(L=L, n_base=120)
    q_coarse = sink_heat_rate(coarse)
    rel_change = abs(q_sink - q_coarse) / abs(q_sink)

    # --- Order-of-accuracy verification on a manufactured problem ---------------
    verify()

    # --- Figure 1: temperature field over the true triangle ---------------------
    fig1 = plot_field(sol.x, sol.y, sol.T, units="\u00b0C",
                      title="Steady conduction on an equilateral triangle")
    p1 = save(fig1, "figures/triangle_temperature.png")

    # --- Figure 2: heat flux q = -k grad T over the temperature field -----------
    fig2, ax = plt.subplots(figsize=(5.6, 4.6))
    ext = [float(sol.x[0]), float(sol.x[-1]), float(sol.y[0]), float(sol.y[-1])]
    im = ax.imshow(sol.T, origin="lower", extent=ext, aspect="equal",
                   cmap="inferno", alpha=0.85)
    cb = fig2.colorbar(im, ax=ax)
    cb.set_label("Temperature (\u00b0C)")
    step = 8
    xx, yy = np.meshgrid(sol.x, sol.y)
    m = sol.inside & np.isfinite(qx) & np.isfinite(qy)
    sel = np.zeros_like(m)
    sel[::step, ::step] = True
    sel &= m
    ax.quiver(xx[sel], yy[sel], qx[sel], qy[sel], color="cyan",
              scale=None, width=0.004, pivot="mid")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("Heat flux q = -k grad T (W/m$^2$)")
    fig2.tight_layout()
    p2 = save(fig2, "figures/triangle_heat_flux.png")

    print("=" * 64)
    print("Steady 2D conduction on an equilateral triangle")
    print("=" * 64)
    print(f"Metal      : AISI 304 stainless steel")
    print(f"k          : {K_METAL:.1f} W/(m.K)")
    print(f"h (base)   : {H_CONV:.1f} W/(m^2.K)   [design choice]")
    print(f"Biot number: Bi = h L / k = {Bi:.3f}")
    print(f"T_infinity : {T_INF:.1f} deg C")
    print("-" * 64)
    print(f"T min / max: {tmin:.3f} / {tmax:.3f} deg C")
    print(f"Residual   : ||A u - b|| = {sol.residual:.3e}")
    print(f"Sink heat rate (base, W/m depth): {q_sink:.3f}")
    print(f"Grid-refine check q_sink(120)->{q_coarse:.3f}, "
          f"q_sink(200)->{q_sink:.3f}, rel change {rel_change:.2%}")
    print("-" * 64)
    print(f"Figure 1: {p1}")
    print(f"Figure 2: {p2}")
