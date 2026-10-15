# Bloxorz maps

`maps.json` contains the original Levels 01–20, keyed `map01` through `map20`.
These are complete levels, not the A/B/C sublevels in the mlsite Quickload menu.

Load a fresh board, including its initial game state:

```python
from BackEnd.init_map import init_map

board = init_map("map01")  # Also accepts "Level 01".
state = board.game_state
```

The loader resolves `maps.json` relative to its own file, independently of the
working directory. An unknown map name raises `ValueError`.

## PNG diagrams

Export all maps as top-down diagrams:

```bash
python -m BackEnd.map_visualization
```

Images are saved to `BackEnd/maps/images/map01.png` through `map20.png`.
To export selected maps or choose an output directory:

```bash
python -m BackEnd.map_visualization map04 map16 --output-dir /tmp/bloxorz-preview
```

Every image includes a legend, coordinates, bridge initial states, switch effects,
and teleport destinations. Closed bridges remain visible with red cross-hatching.
Switch labels use `O` for soft, `X` for heavy, and `T` for split switches.

## Format

- `name`: original level number.
- `block_start`: initial standing-block position `[x, y]`.
- `floor`: ordinary floor positions, including the starting tile.
- `fragile`: fragile tile positions.
- `goal`: the actual exit-hole position, not an intermediate switch checkpoint.
- `bridge`: ID-keyed rectangles with `position`, `w`, `h`, and `initial_open`.
- `switch`: ID-keyed objects with `type`, `position`, and `effects`.
- Split switches also have two `teleport_positions`.
- A `toggle` effect changes the bridge state. A `set` effect uses `target_open`.

Coordinates retain the mlsite 17-by-17 grid: x increases rightwards and y
increases downwards. Positions not represented by any object are empty space.
Floor lists exclude goals, fragile tiles, switches, and bridge regions.
Bridge cells are combined into one rectangle only when their initial state and
all controlling switch effects are identical. Some bridge cells must therefore
remain separate even when they appear next to one another.

## Sources

Geometry, starting positions, exits, fragile tiles, and switch types come from
[mlsite's maps.js](http://www.mlsite.net/bloxors/maps.js), interpreted using
[its solver source](http://www.mlsite.net/bloxors/c0.js).
The [solver page](http://www.mlsite.net/bloxors/) explains that its sublevels
pre-apply bridge effects and omit split-cube reassembly.

Bridge locations, initial bridge states, switch effects, and splitter destinations
are supplemented from
[jacobcoughenour/bloxorz_gba game/levels.json](https://github.com/jacobcoughenour/bloxorz_gba/blob/main/game/levels.json).
That repository's [upstream license](https://github.com/jacobcoughenour/bloxorz_gba/blob/main/LICENSE)
is GNU GPL version 3. No game implementation code from that repository is included.

The supplemental coordinates are translated by `(1, 3)` to match mlsite.
All initial tile types match, except for three additional floor cells in mlsite
Level 03; this dataset retains those mlsite cells. Initial geometry is compared
with the first sublevel of each original level, ignoring the solver's temporary
goal/avoid markers. The actual exit remains the `#` tile.

Retrieved on 2026-10-15. Source SHA-256 digests:

```text
mlsite/maps.js
eb27f03f69fcb517fb22127e9517d6d81d43821610c1c4fb7f9f8515d2c7b89d

bloxorz_gba/game/levels.json
f30ed31fd4259c336a7ecdd4870ab4f74b13c7c17055e9e6cc8a045eac6406fe
```

## Verification

All 20 initial boards were compared cell-by-cell against mlsite, solved using
the project's `GameRules`, and replayed on fresh `Board` instances. The replay
paths are retained in `tests/test_maps.py` for offline regression checks.
This verifies compatibility with the current engine, rather than a Flash GUI.
