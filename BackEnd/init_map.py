"""Load a named map from maps.json into a fresh Board."""

import json
from pathlib import Path

from BackEnd.logic.board import Board
from BackEnd.objects.bridges import Bridge
from BackEnd.objects.switchs import (
    EffectMode, HeavySwitch, SoftSwitch, SplitSwitch, SwitchBridgeLink,
)
from BackEnd.objects.tiles import FloorTile, FragileTile, Goal


MAPS_PATH = Path(__file__).parent / 'maps' / 'maps.json'


def init_map(map_name: str) -> Board:
    """Build an initialized board by key (map01) or level name (Level 01).

    Raise ValueError if the requested map does not exist.
    """
    with MAPS_PATH.open(encoding='utf-8') as file:
        maps = json.load(file)

    data = maps.get(map_name)
    if data is None:
        data = next((level for level in maps.values() if level['name'] == map_name), None)
    if data is None:
        raise ValueError(f"Unknown map: {map_name}")

    board = Board()
    for position in data['floor']:
        board.add_tile(FloorTile(*position))
    for position in data['fragile']:
        board.add_tile(FragileTile(*position))
    board.add_tile(Goal(*data['goal']))

    for bridge_id, bridge in data['bridge'].items():
        board.add_bridge(Bridge(
            *bridge['position'], bridge['w'], bridge['h'], bridge_id,
            bridge.get('initial_open', False),
        ))

    switch_types = {
        'SoftSwitch': SoftSwitch,
        'HeavySwitch': HeavySwitch,
        'SplitSwitch': SplitSwitch,
    }
    for switch_id, switch in data['switch'].items():
        effects = tuple(
            SwitchBridgeLink(
                effect['bridge_id'], EffectMode(effect['effect_mode']),
                effect.get('target_open'),
            )
            for effect in switch['effects']
        )
        options = {}
        if switch['type'] == 'SplitSwitch':
            options['teleport_positions'] = tuple(tuple(p) for p in switch['teleport_positions'])
        board.add_switch(switch_types[switch['type']](
            *switch['position'], switch_id, effects, **options,
        ))

    board.initialize_game_state(tuple(data['block_start']))
    return board
