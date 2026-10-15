from enum import Enum

Position = tuple[int, int]


class Move(Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    SWITCH = "switch"
