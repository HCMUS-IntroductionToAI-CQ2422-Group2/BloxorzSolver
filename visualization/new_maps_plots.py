"""Plots for benchmarks/benchmark_15_new_maps.csv (map21-map35).

Reuses the styling helpers from benchmark_plots.py (the 20-map notebook's
module) but with looser validation: unlike that dataset, 3 of these 60
rows are status="limit" (A* on the 3 largest new maps did not finish
building its heuristic table within the 30s budget), not "solved". Charts
that need a numeric solution length simply skip those 3 cells instead of
requiring a complete solved grid.

Run from the repository root:
    python visualization/new_maps_plots.py
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark_plots import ALGORITHMS, COLORS, MARKERS, CSV_COLUMNS, configure_style, save_figure

MAPS = [f"map{i:02}" for i in range(21, 36)]
METRICS = ["search_time_s", "peak_memory_bytes", "expanded_nodes"]
CSV_PATH = Path(__file__).resolve().parents[1] / "benchmarks" / "benchmark_15_new_maps.csv"
FIGURES_DIR = Path(__file__).resolve().parent / "figures_new_maps"


def load_benchmark(path):
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(data.columns) != CSV_COLUMNS:
        raise ValueError("CSV headers must match schema v1.0.0 exactly")
    if len(data) != len(MAPS) * len(ALGORITHMS):
        raise ValueError(f"Expected {len(MAPS) * len(ALGORITHMS)} rows, got {len(data)}")
    if set(zip(data.map_id, data.algorithm)) != {(m, a) for m in MAPS for a in ALGORITHMS}:
        raise ValueError("Expected exactly 15 maps x 4 algorithms, one trial per pair")
    if not set(data.status) <= {"solved", "no_solution", "limit", "error"}:
        raise ValueError("Unknown result status")

    for column in ["search_time_s", "peak_memory_bytes", "expanded_nodes", "path_cost"]:
        data[column] = pd.to_numeric(data[column].replace("", np.nan), errors="raise")
    data["started_at_utc"] = pd.to_datetime(data.started_at_utc, utc=True, errors="raise")
    solved = data.status.eq("solved")
    if not (data.loc[solved, "solution_valid"] == "true").all():
        raise ValueError("A solved row replayed invalid -- inspect before plotting")
    data["algorithm"] = pd.Categorical(data.algorithm, categories=ALGORITHMS, ordered=True)
    data["memory_mib"] = data.peak_memory_bytes / 1048576
    data["solved"] = solved
    return data.sort_values(["map_id", "algorithm"]).reset_index(drop=True)


def stamp(fig, data, note):
    commit = data.git_commit.iloc[0][:7]
    date = data.started_at_utc.min().strftime("%Y-%m-%d UTC")
    fig.text(.02, .045, note, ha="left", va="bottom", fontsize=9, color="#465261")
    fig.text(.02, .015,
             f"Source: benchmark_15_new_maps.csv | {date} | 15 maps, 1 run per algorithm/map | solver {commit}",
             ha="left", va="bottom", fontsize=8, color="#657181")
    fig.tight_layout(rect=(0, .09, 1, 1))
    return fig


def metric_matrix(data, metric, solved_only=False):
    frame = data[data.solved] if solved_only else data
    return frame.pivot(index="map_id", columns="algorithm", values=metric).reindex(index=MAPS, columns=ALGORITHMS)


def plot_runtime_heatmap(data):
    matrix = metric_matrix(data, "search_time_s")
    timed_out = metric_matrix(data, "solved") == False  # noqa: E712 (NaN-safe)
    fig, ax = plt.subplots(figsize=(9, 8))
    from matplotlib.colors import LogNorm
    from matplotlib.ticker import FuncFormatter
    norm = LogNorm(vmin=matrix.to_numpy().min(), vmax=matrix.to_numpy().max())
    plot = ax.imshow(matrix, norm=norm, cmap="YlGnBu", aspect="auto")
    for row, map_id in enumerate(MAPS):
        for col, algorithm in enumerate(ALGORITHMS):
            value = matrix.loc[map_id, algorithm]
            label = f"{value:.3f}" + ("*" if timed_out.loc[map_id, algorithm] else "")
            ax.text(col, row, label, ha="center", va="center",
                    color="white" if norm(value) > .62 else "#17212d", fontsize=10)
    ax.set(xticks=range(4), xticklabels=ALGORITHMS, yticks=range(15), yticklabels=MAPS,
           xlabel="Algorithm", ylabel="Map ID",
           title="1. Search time on 15 new maps (map21-map35)")
    colorbar = fig.colorbar(plot, ax=ax, pad=.03)
    colorbar.set_label("Search time (seconds; logarithmic color scale)")
    colorbar.ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    return stamp(fig, data, "* = hit the 30s time limit before finishing (A* heuristic table still building). Cell value is the elapsed time, not a solved runtime.")


def plot_distribution(data, metric, ylabel, title, note):
    fig, ax = plt.subplots(figsize=(10, 6))
    groups = [data[data.algorithm == a][metric].dropna().to_numpy() for a in ALGORITHMS]
    box = ax.boxplot(groups, tick_labels=ALGORITHMS, patch_artist=True, showfliers=False,
                     widths=.48, medianprops={"color": "#17212d", "linewidth": 2},
                     whiskerprops={"color": "#7a8793"}, capprops={"color": "#7a8793"})
    for index, (algorithm, values, patch) in enumerate(zip(ALGORITHMS, groups, box["boxes"]), 1):
        patch.set_facecolor(COLORS[algorithm]); patch.set_alpha(.15)
        jitter = np.linspace(-.16, .16, len(values))
        ax.scatter(index + jitter, values, color=COLORS[algorithm], marker=MARKERS[algorithm],
                   s=30, alpha=.8, edgecolors="white", linewidth=.5, zorder=3)
        median = np.median(values)
        ax.text(index + .27, median, f"{median:.3f}", va="center", fontsize=10, color=COLORS[algorithm])
    ax.set(yscale="log", xlabel="Algorithm", ylabel=ylabel, title=title, xlim=(.5, 4.65))
    ax.grid(axis="y", which="major", alpha=.2)
    return stamp(fig, data, note)


def plot_expanded_nodes(data):
    matrix = metric_matrix(data, "expanded_nodes", solved_only=True)
    fig, ax = plt.subplots(figsize=(11, 6))
    series = [("BFS", "BFS = UCS"), ("DFS", "DFS"), ("A*", "A* (12/15 maps; 3 timed out)")] \
        if matrix.BFS.equals(matrix.UCS) else [(a, a) for a in ALGORITHMS]
    for algorithm, label in series:
        ax.plot(range(15), matrix[algorithm], label=label, color=COLORS[algorithm],
                marker=MARKERS[algorithm], markersize=6, linewidth=1.6)
    ax.set(xticks=range(15), xticklabels=MAPS, yscale="log", xlabel="Map ID (categorical)",
           ylabel="Expanded nodes (log scale)", title="2. Search effort by map")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", which="major", alpha=.2)
    ax.legend(frameon=False, ncol=3, loc="upper left")
    return stamp(fig, data, "A* points are missing for map32/34/35 -- it never finished its heuristic preprocessing within 30s on those.")


def plot_solution_lengths(data):
    matrix = metric_matrix(data, "path_cost", solved_only=True)
    if not matrix.BFS.equals(matrix.UCS):
        raise ValueError("BFS/UCS solution-length agreement failed: inspect before plotting")
    fig, ax = plt.subplots(figsize=(11, 9))
    for index, map_id in enumerate(MAPS):
        baseline, dfs = matrix.loc[map_id, ["BFS", "DFS"]]
        ax.plot([baseline, dfs], [index, index], color="#cbd2d9", linewidth=2)
        ax.scatter(baseline, index, c=COLORS["BFS"], s=38, label="BFS = UCS" if index == 0 else None, zorder=3)
        ax.scatter(dfs, index, c=COLORS["DFS"], marker="s", s=35, label="DFS" if index == 0 else None, zorder=4)
        astar = matrix.loc[map_id, "A*"]
        if pd.notna(astar):
            ax.scatter(astar, index, c=COLORS["A*"], marker="D", s=35,
                       label="A*" if index == 0 else None, zorder=5)
        ax.text(dfs * 1.1, index, f"{int(dfs)} / {dfs/baseline:.1f}x BFS", va="center", fontsize=9)
    ax.set(yticks=range(15), yticklabels=MAPS, xscale="log",
           xlabel="Solution length (actions; log scale)", ylabel="Map ID",
           title="3. Path quality: DFS vs. shortest solutions (new maps)")
    ax.invert_yaxis()
    ax.grid(axis="x", which="major", alpha=.2)
    ax.legend(frameon=False, loc="lower right")
    return stamp(fig, data, "A* markers omitted for map32/34/35 (timed out). Every action, including SWITCH, costs 1; these maps have none.")


def plot_relative_profile(data):
    labels = ["Time", "Peak memory", "Expanded nodes"]
    metrics = ["search_time_s", "memory_mib", "expanded_nodes"]
    ratios = {}
    for label, metric in zip(labels, metrics):
        bfs = metric_matrix(data, metric)["BFS"]
        full = metric_matrix(data, metric)
        ratios[label] = full.div(bfs, axis=0).median()
    profile = pd.DataFrame(ratios).loc[["DFS", "UCS", "A*"]]
    astar_n = int(data[(data.algorithm == "A*") & data.solved].shape[0])
    transformed = np.log2(profile.to_numpy())
    extent = max(abs(np.nanmin(transformed)), abs(np.nanmax(transformed)), 1)
    from matplotlib.colors import TwoSlopeNorm
    norm = TwoSlopeNorm(vmin=-extent, vcenter=0, vmax=extent)
    fig, ax = plt.subplots(figsize=(9, 5))
    plot = ax.imshow(transformed, norm=norm, cmap="RdBu_r", aspect="auto")
    for row in range(3):
        for col in range(3):
            ax.text(col, row, f"{profile.iloc[row, col]:.2f}x", ha="center", va="center", fontsize=13,
                    color="white" if abs(transformed[row, col]) / extent > .65 else "#17212d")
    ax.set(xticks=range(3), xticklabels=labels, yticks=range(3), yticklabels=profile.index,
           xlabel="Metric (all lower is better)", ylabel="Algorithm / BFS baseline",
           title="4. Median paired performance ratios relative to BFS")
    colorbar = fig.colorbar(plot, ax=ax, pad=.03)
    colorbar.set_label("log2(ratio): 0 = BFS, negative = lower, positive = higher")
    return stamp(fig, data, f"A* row uses only the {astar_n}/15 maps it solved within 30s. Divide each map's metric by BFS on that map, then take the median.")


def main():
    configure_style()
    data = load_benchmark(CSV_PATH)
    figures = {
        "01_runtime_heatmap": plot_runtime_heatmap(data),
        "02_expanded_nodes": plot_expanded_nodes(data),
        "03_solution_lengths": plot_solution_lengths(data),
        "04_memory_distribution": plot_distribution(
            data, "memory_mib", "Peak Python allocations (MiB; log scale)",
            "Memory distribution across 15 new maps",
            "1 MiB = 1,048,576 bytes. Includes the 3 A* rows that timed out (still allocated a partial heuristic table)."),
        "05_relative_to_bfs": plot_relative_profile(data),
    }
    for name, fig in figures.items():
        save_figure(fig, FIGURES_DIR, name)
        plt.close(fig)
    print(f"wrote {len(figures)} figures to {FIGURES_DIR}")


if __name__ == "__main__":
    main()
