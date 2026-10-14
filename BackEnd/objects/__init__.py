"""Canonical object definitions shared by game rules, GUI and solvers."""
from .sharing import Move, Position
from .blocks import BlockState, GameState, Orientation
from .tiles import Tile, FloorTile, EmptyCell, Goal, FragileTile
from .bridges import Bridge
from .switchs import EffectMode, SwitchBridgeLink, Switch, SoftSwitch, HeavySwitch, SplitSwitch

__all__ = [
    "Move", "Position", "BlockState", "GameState", "Orientation", "Tile", "FloorTile",
    "EmptyCell", "Goal", "FragileTile", "Bridge", "EffectMode", "SwitchBridgeLink",
    "Switch", "SoftSwitch", "HeavySwitch", "SplitSwitch",
]
