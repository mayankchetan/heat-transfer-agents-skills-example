"""Plotting helpers for 2D heat-solver results.

The solver returns NumPy arrays; these helpers visualize them and nothing else, so
plotting stays out of the numerical core. Convention: fields are shaped (ny, nx) and
indexed T[i, j] with i = row (y) and j = column (x).

Run `python plot_field.py --demo` to render a sample figure and confirm styling.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure


def _extent(x: np.ndarray, y: np.ndarray) -> list[float]:
    return [float(x[0]), float(x[-1]), float(y[0]), float(y[-1])]


def plot_field(
    x: np.ndarray,
    y: np.ndarray,
    T: np.ndarray,
    *,
    units: str = "K",
    title: str | None = None,
    cmap: str = "inferno",
    ax: plt.Axes | None = None,
) -> Figure:
    """Filled heatmap of a 2D temperature field against physical coordinates."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(5.2, 4.2))
    else:
        fig = ax.figure
    im = ax.imshow(
        T, origin="lower", extent=_extent(x, y), aspect="equal", cmap=cmap
    )
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(f"Temperature ({units})")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    if title:
        ax.set_title(title)
    fig.tight_layout()
    return fig


def plot_profile(
    coord: np.ndarray,
    T_line: np.ndarray,
    *,
    xlabel: str,
    units: str = "K",
    label: str | None = None,
    ax: plt.Axes | None = None,
) -> Figure:
    """1D line-out of temperature along a coordinate."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(5.2, 3.6))
    else:
        fig = ax.figure
    ax.plot(coord, T_line, marker="", label=label)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(f"Temperature ({units})")
    if label:
        ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def plot_comparison(
    x: np.ndarray,
    y: np.ndarray,
    T_num: np.ndarray,
    T_exact: np.ndarray,
    *,
    units: str = "K",
) -> Figure:
    """Numeric, analytical, and error panels side by side.

    The error panel's title reports the maximum absolute error, useful as a quick
    verification readout.
    """
    err = T_num - T_exact
    max_err = float(np.max(np.abs(err)))
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.0))
    ext = _extent(x, y)

    for ax, data, title, cmap in (
        (axes[0], T_num, "Numerical", "inferno"),
        (axes[1], T_exact, "Analytical", "inferno"),
    ):
        im = ax.imshow(data, origin="lower", extent=ext, aspect="equal", cmap=cmap)
        fig.colorbar(im, ax=ax).set_label(f"T ({units})")
        ax.set_title(title)
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")

    vmax = max(max_err, 1e-30)
    im = axes[2].imshow(
        err, origin="lower", extent=ext, aspect="equal", cmap="coolwarm",
        vmin=-vmax, vmax=vmax,
    )
    fig.colorbar(im, ax=axes[2]).set_label(f"Error ({units})")
    axes[2].set_title(f"Error (max |ΔT| = {max_err:.3e} {units})")
    axes[2].set_xlabel("x (m)")
    axes[2].set_ylabel("y (m)")
    fig.tight_layout()
    return fig


def save(fig: Figure, path: str | Path) -> Path:
    """Save a figure, creating parent folders as needed."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    return out


def _demo() -> None:
    nx, ny = 60, 50
    x = np.linspace(0.0, 1.2, nx)
    y = np.linspace(0.0, 1.0, ny)
    xx, yy = np.meshgrid(x, y)
    # A smooth sample field standing in for a real solution.
    T = 300.0 + 80.0 * np.sin(np.pi * xx / x[-1]) * np.sinh(np.pi * yy / x[-1]) / np.sinh(np.pi)
    fig = plot_field(x, y, T, title="Demo temperature field")
    out = save(fig, "figures/demo_field.png")
    print(f"Wrote {out}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Heat-result plotting helpers.")
    parser.add_argument("--demo", action="store_true", help="Render a sample field.")
    args = parser.parse_args()
    if args.demo:
        _demo()
    else:
        parser.print_help()
