"""Run BFS/DFS/UCS/A* over a set of maps and write a schema v1.0.0 CSV.

See docs/benchmark_csv_schema.md for the column contract. Each map is
loaded fresh per algorithm (init_map never shares state between calls),
measured with BackEnd.Benchmark.Benchmark via BackEnd.search.solve, and
independently replayed with GameRules to populate solution_valid.

Usage (from the repository root):
    python benchmarks/run_benchmark.py --maps map21-map35 \
        --out benchmarks/benchmark_15_new_maps.csv
"""
import argparse
import csv
import hashlib
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from BackEnd.init_map import init_map
from BackEnd.logic.game_rules import GameRules
from BackEnd.search import SOLVERS, solve

CSV_COLUMNS = [
    "schema_version", "run_id", "started_at_utc", "git_commit", "map_id",
    "algorithm", "trial", "status", "search_time_s", "peak_memory_bytes",
    "expanded_nodes", "solution_length", "path_cost", "solution_valid",
    "time_limit_s", "max_nodes", "actions", "message", "python_version",
    "platform", "maps_sha256",
]
MAPS_JSON = REPO_ROOT / "BackEnd" / "maps" / "maps.json"


def parse_map_range(spec):
    """'map21-map35' or 'map21,map22' or a single 'map21' -> ['map21', ...]."""
    if "-" in spec and "," not in spec:
        start, end = spec.split("-")
        start_n, end_n = int(start[3:]), int(end[3:])
        return [f"map{n:02d}" for n in range(start_n, end_n + 1)]
    return [token.strip() for token in spec.split(",")]


def git_commit():
    out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                          capture_output=True, text=True, check=True)
    return out.stdout.strip()


def verify_replay(board, start_state, actions):
    rules = GameRules(board)
    state = start_state
    for action in actions:
        state = rules.apply_action(state, action)
        if state is None:
            return False
    return rules.is_goal(state)


def run(map_ids, algorithms, max_nodes, time_limit, out_path):
    run_id = str(uuid.uuid4())
    commit = git_commit()
    maps_sha = hashlib.sha256(MAPS_JSON.read_bytes()).hexdigest()
    py_version = platform.python_version()
    plat = platform.platform()

    unknown = set(algorithms) - set(SOLVERS)
    if unknown:
        raise ValueError(f"Unknown algorithm(s): {sorted(unknown)}; choose from {sorted(SOLVERS)}")

    rows = []
    for map_id in map_ids:
        for algorithm in algorithms:
            board = init_map(map_id)
            start_state = board.game_state
            started_at = datetime.now(timezone.utc).isoformat()
            result = solve(board, start_state, algorithm,
                            max_nodes=max_nodes, time_limit=time_limit)
            solved = result.status == "solved"
            solution_valid = ""
            if solved:
                solution_valid = "true" if verify_replay(board, start_state, result.actions) else "false"
            rows.append({
                "schema_version": "1.0.0",
                "run_id": run_id,
                "started_at_utc": started_at,
                "git_commit": commit,
                "map_id": map_id,
                "algorithm": algorithm,
                "trial": 1,
                "status": result.status,
                "search_time_s": result.search_time_s,
                "peak_memory_bytes": result.peak_memory_bytes,
                "expanded_nodes": result.expanded_nodes,
                "solution_length": result.path_cost if solved else "",
                "path_cost": result.path_cost if solved else "",
                "solution_valid": solution_valid,
                "time_limit_s": time_limit,
                "max_nodes": max_nodes,
                "actions": " ".join(action.value for action in result.actions) if solved else "",
                "message": result.message,
                "python_version": py_version,
                "platform": plat,
                "maps_sha256": maps_sha,
            })
            print(f"{map_id:8s} {algorithm:4s} {result.status:10s} "
                  f"time={result.search_time_s:.3f}s nodes={result.expanded_nodes} "
                  f"len={result.path_cost if solved else '-'} valid={solution_valid}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", required=True,
                         help="'map21-map35', 'map21,map22', or a single map id")
    parser.add_argument("--algorithms", default="BFS,DFS,UCS,A*")
    parser.add_argument("--max-nodes", type=int, default=150_000)
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    run(
        map_ids=parse_map_range(args.maps),
        algorithms=[a.strip() for a in args.algorithms.split(",")],
        max_nodes=args.max_nodes,
        time_limit=args.time_limit,
        out_path=Path(args.out),
    )
