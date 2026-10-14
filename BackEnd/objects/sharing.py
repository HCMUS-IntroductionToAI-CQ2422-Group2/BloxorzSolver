"""Shared coordinates and actions. Position is (row, column)."""
from enum import Enum

Position = tuple[int, int]


class Move(Enum):
    LEFT = 0
    RIGHT = 1
    UP = 2
    DOWN = 3
    SWITCH = 4
