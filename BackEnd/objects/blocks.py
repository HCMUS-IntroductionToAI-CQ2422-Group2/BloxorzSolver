from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from BackEnd.objects.sharing import Position


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
