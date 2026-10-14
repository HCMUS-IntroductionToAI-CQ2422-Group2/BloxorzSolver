"""Tile coordinates use x=column, y=row; returned positions use (row, col)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from .blocks import BlockState, GameState

from .sharing import Position


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
