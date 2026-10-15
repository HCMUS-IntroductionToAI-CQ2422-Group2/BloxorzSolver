from dataclasses import dataclass
from typing import TYPE_CHECKING
from .tiles import Tile
from .sharing import Position

if TYPE_CHECKING:
    from .blocks import BlockState
    from .sharing import GameState


@dataclass(frozen=True)
class Bridge(Tile):
    w: int
    h: int
    bridge_id: str
    initial_open: bool = False
    type: str = "Bridge"

    def get_positions(self) -> tuple[Position, ...]:
        positions = []
        for dx in range(self.w):
            for dy in range(self.h):
                positions.append((self.x + dx, self.y + dy))
        return tuple(positions)
    
    def is_open(self, state: 'GameState') -> bool:
        return self.bridge_id in state.open_bridges

    def can_support(self, block: 'BlockState', state: 'GameState') -> bool:
        return self.is_open(state)