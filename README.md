# Bloxorz Search Lab

Python desktop game built with Pygame. Play manually or solve any of the 20
stages with the team's BFS, DFS, UCS and A* solver classes.

## Run

Use Python 3.10 or newer. Create and activate a virtual environment, then run:

```sh
python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows PowerShell instead: .\.venv\Scripts\Activate.ps1
python -m pip install pygame-ce==2.5.8
python main.py
```

`pygame-ce` provides `import pygame`; do not install it alongside the original
`pygame` package. The full `requirements.txt` also includes report plotting
packages pinned for older Python versions; use Python 3.11 for that file.

## Play manually

- Arrow keys / WASD roll along the visible isometric edges. Space changes the
  active cube after a split. One move can wait while an animation finishes.
- Stand the intact block on the goal to win. Invalid moves trigger a fall and
  restart. R or Restart resets the stage.
- Stages opens the level selector. Manual campaign stages unlock through wins;
  best scores are saved in `.save/progress.json`.

## Solve by algorithm

1. Select **Solve by algorithm**. All stages are available in this mode.
2. Choose **BFS**, **DFS**, **UCS** or **A\***, then press **Run**. Search starts
   from the current board position, including bridge states and active cube.
3. Read the benchmark: elapsed time, peak Python allocations, expanded nodes
   and solution moves/cost. Results distinguish solved, no solution, limit and
   error; an already-solved input has a valid zero-move solution.
4. Use **Replay / Pause** or **Step** to inspect the solution. Playback speed is
   adjustable from 1 to 10 moves/second. Replaying again restores the search's
   starting state. Manual moves discard the old solution and measurements.
5. **Export CSV** appends the result, map, starting state and action sequence to
   `output/search_results.csv`.

Search runs in a spawned process, capped at 30 seconds / 150,000 expanded nodes.
Cancel or Escape stops it. Restarting, changing stages, returning to manual mode
or closing the game disposes of the worker. A separate UI deadline also stops an
unresponsive worker. Escape pauses replay and closes menus.

Solver replays do not award campaign stars or unlock stages. Returning to manual
mode resets the stage (or returns to stage 1 if the selected stage is locked).
Restart before each run to compare algorithms from the same initial state.

## Algorithms and benchmark

- `BackEnd/Solver/`: BFS uses FIFO; DFS uses LIFO; UCS prioritizes path cost;
  A* prioritizes path cost plus the existing relaxed-board heuristic.
- `BackEnd/Benchmark.py`: `Benchmark` wraps solver construction and execution;
  the shared `BackEnd/Solver/SearchResult.py` carries measurements and status to the UI. This centralizes the
  timing / `tracemalloc` wrapper proposed in the team's BFS/Benchmark branch.
- `BackEnd/search.py`: dispatches to the four solver classes and defines the
  worker entry point. Direct BFS/UCS/A* `solver.solve(state)` calls return an
  action list or `None`; DFS retains main's `SearchResult` return type.
  `search.solve(board, state, algorithm)` returns the same `SearchResult` type
  for all four algorithms. BFS also retains `_search(state)` for callers that
  need the goal node and expanded-node count.
- `FrontEnd/app.py`: controls, worker lifecycle, benchmark panel and CSV export.
- `FrontEnd/controller.py`: gameplay and replay state.
- `GameRules` remains the authority for movement, switches and bridges.

Every action, including switching cubes, costs 1. BFS and UCS minimize the
number of moves; DFS does not guarantee a shortest solution. A* uses the team's
relaxed-board distance table, including split states and teleportation.

Measurements include solver construction, A* heuristic preparation and tracing
overhead; they exclude UI drawing, process startup and replay. Peak memory is
**Python allocations**, not total process RAM. Expanded nodes count successor
generation, excluding goal nodes, obsolete heap entries and A* preprocessing.
If the worker crashes or is forcibly stopped, unavailable counters display as
unavailable, rather than as measured zeros.

## Verification

```sh
python -m pip install pytest
python -m pytest -q
# Headless screenshot on macOS / Linux:
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python main.py --frames 3 --screenshot output/gui.png
```

Tests cover solver optimality/replay, shared measurements, resource limits,
spawned workers, cancellation, UI controls, campaign progress and game mechanics.
Record any AI assistance and source references in the project report.
