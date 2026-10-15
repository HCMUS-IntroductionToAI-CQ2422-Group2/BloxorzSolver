from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

from BackEnd.objects.blocks import BlockState
from BackEnd.objects.sharing import Position
from BackEnd.objects.tiles import Tile


class EffectMode(str, Enum):
    TOGGLE = "toggle"
    SET = "set"


@dataclass(frozen=True)
class SwitchBridgeLink:
    bridge_id: str
    effect_mode: EffectMode
    target_open: bool | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.effect_mode, EffectMode):
            raise ValueError("effect_mode must be an EffectMode")
        if self.effect_mode == EffectMode.SET and type(self.target_open) is not bool:
            raise ValueError("SET requires a boolean target_open")


@dataclass(frozen=True)
class Switch(Tile):
    switch_id: str
    effects: tuple[SwitchBridgeLink, ...] = ()
    type: ClassVar[str] = "Switch"

    def __post_init__(self) -> None:
        object.__setattr__(self, "effects", tuple(self.effects))

    def is_activated(self, block: BlockState) -> bool:
        return any(block.occupies(position) for position in self.get_positions())


class SoftSwitch(Switch):
    type = "SoftSwitch"


class HeavySwitch(Switch):
    type = "HeavySwitch"

    def is_activated(self, block: BlockState) -> bool:
        return block.is_standing() and super().is_activated(block)


@dataclass(frozen=True)
class SplitSwitch(Switch):
    teleport_positions: tuple[Position, Position] = field(kw_only=True)
    type: ClassVar[str] = "SplitSwitch"

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "teleport_positions",
                           tuple(tuple(p) for p in self.teleport_positions))

    def is_activated(self, block: BlockState) -> bool:
        return block.is_standing() and super().is_activated(block)
