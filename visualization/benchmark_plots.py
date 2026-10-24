"""Validated, reproducible plots for the benchmark CSV schema v1.0.0."""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, TwoSlopeNorm
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd


ALGORITHMS = ["BFS", "DFS", "UCS", "A*"]
MAPS = [f"map{i:02}" for i in range(1, 21)]
COLORS = {"BFS": "#2563a6", "DFS": "#c06820", "UCS": "#23836b", "A*": "#884b9f"}
MARKERS = {"BFS": "o", "DFS": "s", "UCS": "^", "A*": "D"}
CSV_COLUMNS = [
    "schema_version", "run_id", "started_at_utc", "git_commit", "map_id",
    "algorithm", "trial", "status", "search_time_s", "peak_memory_bytes",
    "expanded_nodes", "solution_length", "path_cost", "solution_valid",
    "time_limit_s", "max_nodes", "actions", "message", "python_version",
    "platform", "maps_sha256",
]
METRICS = ["search_time_s", "peak_memory_bytes", "expanded_nodes", "solution_length"]


def locate_repository(start=None):
    """Work when launched from either the repository or visualization folder."""
    start = Path(start or Path.cwd()).resolve()
    for candidate in (start, *start.parents):
        if (candidate / "benchmarks/benchmark_20_maps.csv").is_file():
            return candidate
    raise FileNotFoundError("Cannot find benchmarks/benchmark_20_maps.csv above this folder")


def load_benchmark(path):
    """Reject duplicates/mixed runs and invalid values before comparing maps."""
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(data.columns) != CSV_COLUMNS:
        raise ValueError("CSV headers must match schema v1.0.0 exactly")
    if set(data["schema_version"]) != {"1.0.0"}:
        raise ValueError("Unsupported schema version")
    for column in ("run_id", "git_commit", "maps_sha256", "python_version", "platform"):
        if data[column].nunique() != 1 or data[column].iloc[0] == "":
            raise ValueError(f"Expected one non-empty {column} for this analysis")
    if data.duplicated(["run_id", "map_id", "algorithm", "trial"]).any():
        raise ValueError("Duplicate benchmark key")
    expected = {(map_id, algorithm) for map_id in MAPS for algorithm in ALGORITHMS}
    if len(data) != 80 or set(zip(data.map_id, data.algorithm)) != expected:
        raise ValueError("Expected exactly 20 maps × 4 algorithms, one trial per pair")
    if set(data.trial) != {"1"}:
        raise ValueError("This notebook describes single-trial data only")
    if not set(data.status) <= {"solved", "no_solution", "limit", "error"}:
        raise ValueError("Unknown result status")
    if not set(data.solution_valid) <= {"true", "false", ""}:
        raise ValueError("Invalid solution_valid boolean")
    for column in METRICS + ["path_cost", "trial", "time_limit_s", "max_nodes"]:
        data[column] = pd.to_numeric(data[column].replace("", np.nan), errors="raise")
        values = data[column].dropna()
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError(f"Invalid non-negative metric: {column}")
        if column not in ("search_time_s", "time_limit_s") and (values % 1 != 0).any():
            raise ValueError(f"Expected integer values: {column}")
    for column in ("time_limit_s", "max_nodes", "trial"):
        if data[column].isna().any() or data[column].nunique() != 1:
            raise ValueError(f"Inconsistent or missing {column}")
    if (data.time_limit_s <= 0).any():
        raise ValueError("time_limit_s must be positive")
    data["solution_valid"] = data.solution_valid.map({"true": True, "false": False, "": pd.NA}).astype("boolean")
    data["started_at_utc"] = pd.to_datetime(data.started_at_utc, utc=True, errors="raise")
    solved = data.status.eq("solved")
    if data.loc[solved, METRICS + ["path_cost"]].isna().any().any():
        raise ValueError("Solved rows are missing measurements")
    if not data.loc[solved, "solution_valid"].fillna(False).all():
        raise ValueError("Solved results include an unverified/invalid replay")
    actions = data.loc[solved, "actions"].str.split()
    allowed_actions = {"up", "down", "left", "right", "switch"}
    if any(set(sequence) - allowed_actions for sequence in actions):
        raise ValueError("Unknown action in a solution")
    if not actions.str.len().eq(data.loc[solved, "solution_length"]).all():
        raise ValueError("Action count does not match solution_length")
    if not data.loc[solved, "path_cost"].eq(data.loc[solved, "solution_length"]).all():
        raise ValueError("Unit-cost path_cost differs from solution_length")
    terminal_fields = ["solution_length", "path_cost", "solution_valid"]
    if data.loc[~solved, terminal_fields].notna().any().any() or data.loc[~solved, "actions"].ne("").any():
        raise ValueError("Unsolved rows must not contain a solution")
    # These figures compare a complete solved grid, rather than silently
    # dropping failures or turning unavailable measurements into zeros.
    if not solved.all():
        raise ValueError("This complete-grid notebook requires 80 solved rows; inspect failures separately")
    data["algorithm"] = pd.Categorical(data.algorithm, categories=ALGORITHMS, ordered=True)
    data["memory_mib"] = data.peak_memory_bytes / 1048576
    return data.sort_values(["map_id", "algorithm"]).reset_index(drop=True)


def metric_matrix(data, metric):
    return data.pivot(index="map_id", columns="algorithm", values=metric).reindex(index=MAPS, columns=ALGORITHMS)


def summary_table(data):
    rows = []
    for algorithm in ALGORITHMS:
        group = data[data.algorithm == algorithm]
        rows.append({
            "algorithm": algorithm,
            "solved_maps": int(group.status.eq("solved").sum()),
            "median_time_s": group.search_time_s.median(),
            "max_time_s": group.search_time_s.max(),
            "median_memory_mib": group.memory_mib.median(),
            "max_memory_mib": group.memory_mib.max(),
            "median_expanded_nodes": group.expanded_nodes.median(),
            "median_solution_moves": group.solution_length.median(),
        })
    return pd.DataFrame(rows).set_index("algorithm")


def paired_ratios(data, metric):
    matrix = metric_matrix(data, metric)
    if (matrix["BFS"] <= 0).any():
        raise ValueError(f"BFS baseline must be positive for ratios: {metric}")
    return matrix.div(matrix["BFS"], axis=0)


def configure_style():
    mpl.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 11,
        "axes.titlesize": 14, "axes.titleweight": "bold",
        "axes.labelsize": 11, "axes.spines.top": False, "axes.spines.right": False,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "axes.axisbelow": True, "savefig.facecolor": "white",
        "svg.fonttype": "none",
    })


def stamp(fig, data, note):
    commit = data.git_commit.iloc[0][:7]
    date = data.started_at_utc.min().strftime("%Y-%m-%d UTC")
    fig.text(.02, .045, note, ha="left", va="bottom", fontsize=9, color="#465261")
    fig.text(.02, .015,
             f"Source: benchmark_20_maps.csv | {date} | 20 maps, 1 run per algorithm/map | solver {commit}",
             ha="left", va="bottom", fontsize=8, color="#657181")
    fig.tight_layout(rect=(0, .09, 1, 1))
    return fig


def save_figure(fig, output_dir, name):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "svg"):
        fig.savefig(output_dir / f"{name}.{extension}", dpi=170, bbox_inches="tight")


def plot_runtime_heatmap(data):
    matrix = metric_matrix(data, "search_time_s")
    if (matrix <= 0).any().any():
        raise ValueError("Logarithmic runtime heatmap requires positive times")
    fig, ax = plt.subplots(figsize=(10.5, 9.8))
    norm = LogNorm(vmin=matrix.to_numpy().min(), vmax=matrix.to_numpy().max())
    cmap = plt.get_cmap("YlGnBu")
    plot = ax.imshow(matrix, norm=norm, cmap=cmap, aspect="auto")
    for row, map_id in enumerate(MAPS):
        for col, algorithm in enumerate(ALGORITHMS):
            value = matrix.loc[map_id, algorithm]
            ax.text(col, row, f"{value:.3f}", ha="center", va="center",
                    color="white" if norm(value) > .62 else "#17212d", fontsize=10)
    ax.set(xticks=range(4), xticklabels=ALGORITHMS, yticks=range(20), yticklabels=MAPS,
           xlabel="Algorithm", ylabel="Map ID",
           title="1. Search time by map and algorithm")
    colorbar = fig.colorbar(plot, ax=ax, pad=.03)
    colorbar.set_label("Search time (seconds; logarithmic color scale)")
    colorbar.ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
    return stamp(fig, data, "Cell labels are seconds, rounded to 3 decimals. Timing includes A* heuristic construction and tracing.")


def plot_distribution(data, metric, ylabel, title, note):
    fig, ax = plt.subplots(figsize=(11, 6))
    groups = [data[data.algorithm == algorithm][metric].to_numpy() for algorithm in ALGORITHMS]
    if any(np.any(values <= 0) for values in groups):
        raise ValueError("Logarithmic distributions require positive measurements")
    box = ax.boxplot(groups, tick_labels=ALGORITHMS, patch_artist=True, showfliers=False,
                     widths=.48, medianprops={"color": "#17212d", "linewidth": 2},
                     whiskerprops={"color": "#7a8793"}, capprops={"color": "#7a8793"})
    jitter = np.linspace(-.16, .16, len(MAPS))
    for index, (algorithm, values, patch) in enumerate(zip(ALGORITHMS, groups, box["boxes"]), 1):
        patch.set_facecolor(COLORS[algorithm]); patch.set_alpha(.15)
        ax.scatter(index+jitter, values, color=COLORS[algorithm], marker=MARKERS[algorithm],
                   s=30, alpha=.8, edgecolors="white", linewidth=.5, zorder=3)
        median = np.median(values)
        ax.text(index+.27, median, f"{median:.3f}", va="center", fontsize=10, color=COLORS[algorithm])
    ax.set(yscale="log", xlabel="Algorithm", ylabel=ylabel, title=title, xlim=(.5, 4.65))
    ax.grid(axis="y", which="major", alpha=.2)
    return stamp(fig, data, note)


def plot_runtime_distribution(data):
    return plot_distribution(data, "search_time_s", "Search time (seconds; log scale)",
        "2. Runtime distribution across 20 different maps",
        "Dots: individual maps. Box: Q1–Q3, line/label: median, whiskers: 1.5 IQR. Not repeated-trial uncertainty.")


def plot_memory_distribution(data):
    return plot_distribution(data, "memory_mib", "Peak Python allocations (MiB; log scale)",
        "3. Memory distribution across 20 different maps",
        "1 MiB = 1,048,576 bytes. Includes heuristic allocations; excludes total process RAM. Dots show all 20 maps.")


def plot_expanded_nodes(data):
    matrix = metric_matrix(data, "expanded_nodes")
    fig, ax = plt.subplots(figsize=(13.5, 6))
    series = [(algorithm, algorithm) for algorithm in ALGORITHMS]
    if matrix.BFS.equals(matrix.UCS):
        series = [("BFS", "BFS = UCS"), ("DFS", "DFS"), ("A*", "A*")]
    for algorithm, label in series:
        ax.plot(range(20), matrix[algorithm], label=label, color=COLORS[algorithm],
                marker=MARKERS[algorithm], markersize=5, linewidth=1.6)
    ax.set(xticks=range(20), xticklabels=MAPS, yscale="log", xlabel="Map ID (categorical)",
           ylabel="Expanded nodes (log scale)", title="4. Search effort by map")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", which="major", alpha=.2)
    ax.legend(frameon=False, ncol=len(series), loc="upper left")
    return stamp(fig, data, "A* preprocessing is excluded from node counts. Lines connect categorical maps for readability, not a time trend.")


def plot_solution_lengths(data):
    matrix = metric_matrix(data, "solution_length")
    if not (matrix.BFS.equals(matrix.UCS) and matrix.BFS.equals(matrix["A*"])):
        raise ValueError("Shortest-path agreement failed: inspect BFS/UCS/A* results")
    fig, ax = plt.subplots(figsize=(12, 10))
    for index, map_id in enumerate(MAPS):
        baseline, dfs = matrix.loc[map_id, ["BFS", "DFS"]]
        ax.plot([baseline, dfs], [index, index], color="#cbd2d9", linewidth=2)
        ax.scatter(baseline, index, c=COLORS["BFS"], s=38, label="BFS = UCS = A*" if index == 0 else None, zorder=3)
        ax.scatter(dfs, index, c=COLORS["DFS"], marker="s", s=35, label="DFS" if index == 0 else None, zorder=4)
        ax.text(dfs*1.12, index, f"{int(dfs)} moves / {dfs/baseline:.1f}× BFS", va="center", fontsize=9)
    ax.set(yticks=range(20), yticklabels=MAPS, xscale="log", xlim=(5, matrix.DFS.max()*6),
           xlabel="Solution length (actions; log scale)", ylabel="Map ID",
           title="5. Path quality: DFS versus shortest solutions")
    ax.invert_yaxis()
    ax.grid(axis="x", which="major", alpha=.2)
    ax.legend(frameon=False, loc="lower right")
    return stamp(fig, data, "Every action, including SWITCH, costs 1. Labels show DFS length and its ratio to BFS; all paths passed replay.")


def plot_nodes_vs_time(data):
    fig, ax = plt.subplots(figsize=(11.5, 7))
    for algorithm in ALGORITHMS:
        group = data[data.algorithm == algorithm]
        ax.scatter(group.expanded_nodes, group.search_time_s, label=algorithm,
                   color=COLORS[algorithm], marker=MARKERS[algorithm], s=48,
                   alpha=.8, edgecolors="white", linewidth=.5)
    # Label the slowest observed map per algorithm; no fitted causal model.
    offsets = {"BFS": (10, -20), "DFS": (10, -12), "UCS": (10, 10), "A*": (-70, 10)}
    for algorithm in ALGORITHMS:
        group = data[data.algorithm == algorithm]
        row = group.loc[group.search_time_s.idxmax()]
        ax.annotate(f"{algorithm} {row.map_id}", (row.expanded_nodes, row.search_time_s),
                    xytext=offsets[algorithm], textcoords="offset points", fontsize=9,
                    color=COLORS[algorithm])
    ax.set(xscale="log", yscale="log", xlabel="Expanded nodes (log scale)",
           ylabel="Search time (seconds; log scale)", title="6. Fewer expanded nodes do not always mean a faster run")
    ax.margins(x=.18, y=.2)
    ax.grid(which="major", alpha=.2)
    ax.legend(title="Algorithm", frameon=False, loc="lower right")
    return stamp(fig, data, "Each point is one map–algorithm run. Timing includes preprocessing; expanded nodes count only the search phase.")


def plot_relative_profile(data):
    labels = ["Time", "Peak memory", "Expanded nodes", "Solution moves"]
    ratios = pd.DataFrame({label: paired_ratios(data, metric).median()
                           for label, metric in zip(labels, METRICS)}).loc[["DFS", "UCS", "A*"]]
    if (ratios <= 0).any().any():
        raise ValueError("Log-ratio profile requires positive ratios")
    transformed = np.log2(ratios.to_numpy())
    extent = max(abs(transformed.min()), abs(transformed.max()), 1)
    norm = TwoSlopeNorm(vmin=-extent, vcenter=0, vmax=extent)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    plot = ax.imshow(transformed, norm=norm, cmap="RdBu_r", aspect="auto")
    for row in range(3):
        for col in range(4):
            value = ratios.iloc[row, col]
            ax.text(col, row, f"{value:.2f}×", ha="center", va="center", fontsize=13,
                    color="white" if abs(transformed[row, col])/extent > .65 else "#17212d")
    ax.set(xticks=range(4), xticklabels=labels, yticks=range(3), yticklabels=ratios.index,
           xlabel="Metric (all lower is better)", ylabel="Algorithm / BFS baseline",
           title="7. Median paired performance ratios relative to BFS")
    colorbar = fig.colorbar(plot, ax=ax, pad=.03)
    colorbar.set_label("log2(ratio): 0 = BFS, negative = lower, positive = higher")
    return stamp(fig, data, "Divide each map's metric by BFS on that same map, then take the median of 20 ratios. Not a composite score.")
