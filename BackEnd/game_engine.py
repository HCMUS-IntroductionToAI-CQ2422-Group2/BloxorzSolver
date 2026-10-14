"""Pure transitions for GUI and search clients; no solver implementations."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .objects import (
    BlockState, Bridge, GameState, Orientation, Position, Tile,
    Switch, SplitSwitch, EffectMode, Move,
)


@dataclass(frozen=True)
class Board:
    tiles: tuple[tuple[Tile, ...], ...]
    bridges: Mapping[str, Bridge]
    start_position: Position
    goal_position: Position

    def __post_init__(self) -> None:
        # Snapshot caller-owned containers so later edits cannot change transitions.
        object.__setattr__(self, "tiles", tuple(tuple(row) for row in self.tiles))
        object.__setattr__(self, "bridges", MappingProxyType(dict(self.bridges)))
        object.__setattr__(self, "start_position", tuple(self.start_position))
        object.__setattr__(self, "goal_position", tuple(self.goal_position))
        if not self.tiles or not self.tiles[0] or any(len(row) != len(self.tiles[0]) for row in self.tiles):
            raise ValueError("Board must be a non-empty rectangular grid")
        for position in (self.start_position, self.goal_position):
            if not self._in_bounds(position):
                raise ValueError("Start and goal must be inside the board")
        bridge_cells = set()
        for bridge_id, bridge in self.bridges.items():
            if bridge_id != bridge.bridge_id:
                raise ValueError("Bridge dictionary key must match bridge_id")
            if bridge.w <= 0 or bridge.h <= 0:
                raise ValueError("Bridge dimensions must be positive")
            for position in bridge.get_positions():
                if not self._in_bounds(position):
                    raise ValueError("Bridge must be inside the board")
                if position in bridge_cells:
                    raise ValueError("Bridge regions must not overlap")
                bridge_cells.add(position)
        switch_ids = set()
        for r, row in enumerate(self.tiles):
            for c, tile in enumerate(row):
                if (tile.y, tile.x) != (r, c):
                    raise ValueError("Tile coordinates must match its grid position")
                if isinstance(tile, Bridge):
                    raise ValueError("Place bridges in Board.bridges, not the tile grid")
                if not isinstance(tile, Switch):
                    continue
                if tile.switch_id in switch_ids:
                    raise ValueError("Switch IDs must be unique")
                switch_ids.add(tile.switch_id)
                if (r, c) in bridge_cells:
                    raise ValueError("A bridge cannot hide a switch")
                for effect in tile.effects:
                    if effect.bridge_id not in self.bridges:
                        raise ValueError(f"Switch {tile.switch_id}: unknown bridge {effect.bridge_id}")
                if isinstance(tile, SplitSwitch):
                    positions = tile.teleport_positions
                    if len(positions) != 2:
                        raise ValueError(f"Split switch {tile.switch_id}: requires two teleport positions")
                    a, b = positions
                    if abs(a[0] - b[0]) + abs(a[1] - b[1]) <= 1:
                        raise ValueError(f"Split switch {tile.switch_id}: teleport positions must be distinct and non-adjacent")
                    if not all(self._in_bounds(p) for p in positions):
                        raise ValueError("Teleport positions must be inside the board")

    def _in_bounds(self, position: Position) -> bool:
        r, c = position
        return 0 <= r < len(self.tiles) and 0 <= c < len(self.tiles[r])

    def tile_at(self, position: Position) -> Tile | None:
        """Resolve bridge overlays before the underlying floor or void tile."""
        r, c = position
        if not self._in_bounds(position):
            return None
        for bridge in self.bridges.values():
            if bridge.y <= r < bridge.y + bridge.h and bridge.x <= c < bridge.x + bridge.w:
                return bridge
        return self.tiles[r][c]


def initial_state(board: Board) -> GameState:
    state = GameState(
        BlockState((board.start_position,), Orientation.STANDING),
        frozenset(bridge.bridge_id for bridge in board.bridges.values() if bridge.initial_open),
    )
    if not GameRules(board).is_valid(state):
        raise ValueError("Initial block must be supported")
    return state


class GameRules:
    def __init__(self, board: Board):
        self.board = board

    def apply_action(self, state: GameState, action: Move) -> GameState | None:
        if not isinstance(action, Move):
            raise TypeError("action must be a Move enum member")
        if not self.is_valid(state):
            return None
        if action == Move.SWITCH:
            return self._switch_cube(state) if state.block.is_split() else None
        block = self._roll(state.block, action)
        landed = (block.positions[block.active_cube],) if state.block.is_split() else block.positions
        candidate = GameState(block, state.open_bridges)
        if not self.is_valid(candidate):
            return None
        candidate = self._apply_switches(candidate, landed)
        if not self.is_valid(candidate):
            return None
        if state.block.is_split():
            candidate = self._merge_block(candidate)
        return candidate

    def get_valid_actions(self, state: GameState) -> list[Move]:
        return [action for action in Move if self.apply_action(state, action) is not None]

    def is_valid(self, state: GameState) -> bool:
        if not state.open_bridges.issubset(self.board.bridges):
            return False
        block = state.block
        positions = block.positions
        if block.is_standing():
            if len(positions) != 1:
                return False
        else:
            if len(positions) != 2 or positions[0] == positions[1]:
                return False
            (r, c), end = positions
            if block.orientation == Orientation.HORIZONTAL:
                if end != (r, c + 1):
                    return False
            elif block.orientation == Orientation.VERTICAL:
                if end != (r + 1, c):
                    return False
            elif not block.is_split():
                return False
        return all((tile := self.board.tile_at(p)) is not None
                   and tile.can_support(block, state) for p in positions)

    def is_goal(self, state: GameState) -> bool:
        return (self.is_valid(state) and state.block.is_standing()
                and state.block.positions == (self.board.goal_position,))

    def _roll(self, block: BlockState, direction: Move) -> BlockState:
        dr, dc = {Move.UP: (-1, 0), Move.DOWN: (1, 0),
                  Move.LEFT: (0, -1), Move.RIGHT: (0, 1)}[direction]
        if block.is_split():
            positions = list(block.positions)
            r, c = positions[block.active_cube]
            positions[block.active_cube] = (r + dr, c + dc)
            return BlockState.split(tuple(positions), block.active_cube)
        r, c = block.positions[0]
        if block.is_standing():
            return BlockState(((r + dr, c + dc), (r + 2 * dr, c + 2 * dc)),
                              Orientation.VERTICAL if dr else Orientation.HORIZONTAL)
        if block.orientation == Orientation.HORIZONTAL and dc:
            return BlockState(((r, c + (2 if dc > 0 else -1)),), Orientation.STANDING)
        if block.orientation == Orientation.VERTICAL and dr:
            return BlockState(((r + (2 if dr > 0 else -1), c),), Orientation.STANDING)
        return BlockState(tuple((r + dr, c + dc) for r, c in block.positions), block.orientation)

    def _apply_switches(self, state: GameState, landed: tuple[Position, ...]) -> GameState:
        # Select against the landing block, before any effects or teleportation.
        switches = [tile for p in set(landed)
                    if isinstance((tile := self.board.tile_at(p)), Switch)
                    and tile.is_activated(state.block)]
        for switch in sorted(switches, key=lambda switch: switch.switch_id):
            state = self._update_bridges(state, switch)
            if isinstance(switch, SplitSwitch):
                state = self._split_block(state, switch)
        return state

    def _update_bridges(self, state: GameState, switch: Switch) -> GameState:
        opened = set(state.open_bridges)
        for effect in switch.effects:
            if effect.effect_mode == EffectMode.TOGGLE:
                opened.symmetric_difference_update((effect.bridge_id,))
            elif effect.target_open:
                opened.add(effect.bridge_id)
            else:
                opened.discard(effect.bridge_id)
        return GameState(state.block, frozenset(opened))

    def _split_block(self, state: GameState, switch: SplitSwitch) -> GameState:
        # Teleport selects canonical cube 0, regardless of the order in the stage.
        return GameState(BlockState.split(tuple(sorted(switch.teleport_positions))), state.open_bridges)

    def _merge_block(self, state: GameState) -> GameState:
        if not state.block.is_split():
            return state
        (r1, c1), (r2, c2) = state.block.positions
        if abs(r1 - r2) + abs(c1 - c2) != 1:
            return state
        orientation = Orientation.HORIZONTAL if r1 == r2 else Orientation.VERTICAL
        return GameState(BlockState(state.block.positions, orientation), state.open_bridges)

    def _switch_cube(self, state: GameState) -> GameState:
        return GameState(BlockState.split(state.block.positions, 1 - state.block.active_cube),
                         state.open_bridges)
