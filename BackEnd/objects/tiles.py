from dataclasses import dataclass
from typing import ClassVar

from BackEnd.objects.blocks import BlockState, GameState
from BackEnd.objects.sharing import Position


@dataclass(frozen=True)
class Tile:
    x: int
    y: int
    type: ClassVar[str] = "Tile"

    def get_positions(self) -> tuple[Position, ...]:
        return ((self.x, self.y),)

    def can_support(self, block: BlockState, state: GameState) -> bool:
        return True


class FloorTile(Tile):
    type = "Floor"

    def can_support(self, block: BlockState, state: GameState) -> bool:
        return True


class EmptyCell(Tile):
    type = "Empty"

    def can_support(self, block: BlockState, state: GameState) -> bool:
        return False


class Goal(Tile):
    type = "Goal"

    def can_support(self, block: BlockState, state: GameState) -> bool:
        return True


class FragileTile(Tile):
    type = "Fragile"

    def can_support(self, block: BlockState, state: GameState) -> bool:
        return not block.is_standing()
