# Current GUI update

The game now uses a procedural mountain background and isometric wooden blocks.
Menu opens the stage selector; the lightbulb opens BFS / DFS / UCS / A* choices.
These choices are placeholders only: GUI search execution is disconnected pending
future backend integration. Existing search code is retained but not invoked by
these controls. The earlier solver/replay instructions below describe the previous
version, not the current UI.

# Bloxorz Search Lab

Python desktop GUI using Pygame, connected directly to the existing `Board`,
`GameState`, and `GameRules`. No web server is required.

## Run

Python 3.10 or newer. From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-gui.txt
.\.venv\Scripts\python main.py
```

`pygame-ce` provides `import pygame`; do not install it alongside the original
`pygame` distribution in the same environment. The original report plotting
dependencies remain in `requirements.txt`; their pinned versions target older
Python versions (use Python 3.11 for that full requirements file).

## Controls

- Select any of the 20 numbered stages. New game and Restart reset the selected
  stage, including its initial bridges. R is the restart shortcut.
- Arrow keys or WASD roll the block. Space changes the active split cube.
  A mint outline identifies that cube. Space is ignored for an intact block.
- Land upright in the dark, mint-outlined goal to win. An illegal roll shows a
  loss message and preserves the last supported position until restart.
- Orange tiles are fragile. Purple O, X and ( ) tiles are soft, heavy and split
  switches. Mint bridges are open; pink crossed bridges are closed.
- BFS / DFS / UCS / A* solve from the **current position**, including bridge
  states and active cube. Restart first for comparable initial-state runs.
- Replay restores the search's start state; Pause and Step inspect its actions.
  Adjust playback from 1 to 10 actions/second. Manual moves discard old results.
- Escape cancels a search or pauses replay. Selecting a stage, restarting or
  closing the window terminates the worker so stale results cannot be applied.
- Export CSV appends results to `output/search_results.csv`, including the
  starting state and action sequence. The GUI reports search time, traced Python
  peak allocations, expanded nodes and solution actions (Space included).

## Structure

- `FrontEnd/app.py`: window, controls, process lifecycle and CSV export.
- `FrontEnd/controller.py`: gameplay and replay state.
- `FrontEnd/renderer.py`: dynamic board and block rendering.
- `BackEnd/search.py`: self-implemented baseline search algorithms.
- Existing backend rules remain the single authority for movement and switches.

Search runs in a separate spawned process, capped at 30 seconds / 150,000 expanded
nodes. A cap is reported separately from an exhausted unsolvable search. Each
action costs 1, including switching cubes, so UCS and BFS minimize the same
quantity. A* currently uses `h=0` at the goal and `h=1` elsewhere, a consistent,
admissible but weak baseline even with teleportation. Improve and justify the
cost function / heuristic for the report; the GUI does not establish comparative
algorithm performance. Timing includes tracemalloc overhead; memory is peak
Python allocations during search, **not total process RSS**.

## Verification

```powershell
.\.venv\Scripts\python -m pip install pytest
.\.venv\Scripts\python -m pytest -q
$env:SDL_VIDEODRIVER = 'dummy'
.\.venv\Scripts\python main.py --frames 3 --screenshot output/gui.png
Remove-Item Env:SDL_VIDEODRIVER
```

The project report and narrated/subtitled demo video remain separate assignment
deliverables. Record any AI assistance and source references in the report.
