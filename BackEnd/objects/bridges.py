from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from .blocks import BlockState, GameState

from .sharing import Position
from .tiles import Tile


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
