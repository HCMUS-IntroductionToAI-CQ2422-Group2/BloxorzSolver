from dataclasses import dataclass
from __future__ import annotations
from BackEnd.objects.blocks import GameState
from BackEnd.objects.sharing import Move


@dataclass(slots=True, eq=False)
class SearchNode:
    state: GameState
    parent: SearchNode | None = None
    action: Move | None = None
    depth: int = 0
    path_cost: int = 0