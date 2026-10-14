"""Immutable game objects. Positions are (row, col); tile x/y mean col/row."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

Position = tuple[int, int]


@dataclass(frozen=True)
class Tile:
    x: int
    y: int
    type: ClassVar[str] = "Tile"

    def get_positions(self) -> tuple[Position, ...]:
        return ((self.y, self.x),)

    def can_support(self, block: BlockState, state: GameState) -> bool:
        return True


class FloorTile(Tile):
    type = "Floor"


class EmptyCell(Tile):
    type = "Empty"

    def can_support(self, block: BlockState, state: GameState) -> bool:
        return False


class Goal(Tile):
    type = "Goal"


class FragileTile(Tile):
    type = "Fragile"

    def can_support(self, block: BlockState, state: GameState) -> bool:
        return not block.is_standing()


@dataclass(frozen=True)
class Bridge(Tile):
    w: int
    h: int
    bridge_id: str
    initial_open: bool = False
    type: ClassVar[str] = "Bridge"

    def get_positions(self) -> tuple[Position, ...]:
        return tuple((r, c) for r in range(self.y, self.y + self.h)
                     for c in range(self.x, self.x + self.w))

    def is_open(self, state: GameState) -> bool:
        return self.bridge_id in state.open_bridges

    def can_support(self, block: BlockState, state: GameState) -> bool:
        return self.is_open(state)


class EffectMode(str, Enum):
    TOGGLE = "toggle"
    SET = "set"


@dataclass(frozen=True)
class SwitchBridgeLink:
    bridge_id: str
    effect_mode: EffectMode
    target_open: bool | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.effect_mode, EffectMode):
            raise ValueError("effect_mode must be an EffectMode")
        if self.effect_mode == EffectMode.SET and type(self.target_open) is not bool:
            raise ValueError("SET requires a boolean target_open")


@dataclass(frozen=True)
class Switch(Tile):
    switch_id: str
    effects: tuple[SwitchBridgeLink, ...] = ()
    type: ClassVar[str] = "Switch"

    def __post_init__(self) -> None:
        object.__setattr__(self, "effects", tuple(self.effects))

    def is_activated(self, block: BlockState) -> bool:
        return block.occupies((self.y, self.x))


class SoftSwitch(Switch):
    type = "SoftSwitch"


class HeavySwitch(Switch):
    type = "HeavySwitch"

    def is_activated(self, block: BlockState) -> bool:
        return block.is_standing() and super().is_activated(block)


@dataclass(frozen=True)
class SplitSwitch(Switch):
    teleport_positions: tuple[Position, Position] = field(kw_only=True)
    type: ClassVar[str] = "SplitSwitch"

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "teleport_positions",
                           tuple(tuple(p) for p in self.teleport_positions))

    def is_activated(self, block: BlockState) -> bool:
        return block.is_standing() and super().is_activated(block)


class Orientation(str, Enum):
    STANDING = "standing"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    SPLIT = "split"


@dataclass(frozen=True)
class BlockState:
    positions: tuple[Position, ...]
    orientation: Orientation
    active_cube: int = 0

    def __post_init__(self) -> None:
        positions = tuple(tuple(p) for p in self.positions)
        if self.is_split():
            if len(positions) != 2 or self.active_cube not in (0, 1):
                raise ValueError("Split mode requires two cubes and active_cube 0 or 1")
            if positions[0] > positions[1]:
                object.__setattr__(self, "active_cube", 1 - self.active_cube)
        elif self.active_cube != 0:
            raise ValueError("An intact block must have active_cube = 0")
        object.__setattr__(self, "positions", tuple(sorted(positions)))

    @classmethod
    def split(cls, positions: tuple[Position, Position], active_cube: int = 0) -> BlockState:
        """Create split state; normalization preserves the selected physical cube."""
        return cls(positions, Orientation.SPLIT, active_cube)

    def occupies(self, position: Position) -> bool:
        return position in self.positions

    def is_standing(self) -> bool:
        return self.orientation == Orientation.STANDING

    def is_split(self) -> bool:
        return self.orientation == Orientation.SPLIT


@dataclass(frozen=True)
class GameState:
    block: BlockState
    open_bridges: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        object.__setattr__(self, "open_bridges", frozenset(self.open_bridges))
