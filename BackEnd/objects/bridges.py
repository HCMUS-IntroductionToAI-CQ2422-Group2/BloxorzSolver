from dataclasses import dataclass
from typing import ClassVar

from BackEnd.objects.blocks import BlockState, GameState
from BackEnd.objects.sharing import Position
from BackEnd.objects.tiles import Tile


@dataclass(frozen=True)
class Bridge(Tile):
    w: int
    h: int
    bridge_id: str
    initial_open: bool = False
    type: ClassVar[str] = "Bridge"

    def get_positions(self) -> tuple[Position, ...]:
        positions = []
        for dx in range(self.w):
            for dy in range(self.h):
                positions.append((self.x + dx, self.y + dy))
        return tuple(positions)

    def is_open(self, state: GameState) -> bool:
        return self.bridge_id in state.open_bridges

    def can_support(self, block: BlockState, state: GameState) -> bool:
        return self.is_open(state)
