"""Validate the level dataset and replay solutions with the real game rules."""

import json
from pathlib import Path

import pytest

from BackEnd.logic.game_rules import GameRules
from BackEnd.init_map import init_map
from BackEnd.objects.sharing import Move
from BackEnd.Solver.BFSSolver import BFSSolver


NEW_MAPS = [f'map{index:02}' for index in range(21, 36)]


MAPS_PATH = Path(__file__).resolve().parents[1] / 'BackEnd/maps/maps.json'
SOLUTIONS = {
    'map01': 'RDDRRDR',
    'map02': 'URDRRRRUUDRDRRURU',
    'map03': 'URDLURRRRUURRRDDRRDLU',
    'map04': 'ULURRURRRRRRDRDDDDDRULLLLLLD',
    'map05': 'LLLLRLLLLDRDDRRRRDRRRRLLLLDLLLLLL',
    'map06': 'RRRDDRDDRDRULLLUULUUURRDRRULDDRRDDR',
    'map07': 'DLURRRRRDRLULLLLLDRDRDRRRUURDLURUURRRDRDRDLU',
    'map08': 'RRDDDDDURUR',
    'map09': 'RDRRRRRRURDRRRRRUSDLLLLLD',
    'map10': 'RRDDRRDRDDDDDLLLLULLLDURRRDRRRUSLDDDRDDDLDURUUUULLULDLLLLL',
    'map11': 'RRRRULDDDRRRDLULLLUURURRDRULLLDDLLLUURUULDRURDL',
    'map12': 'LDRURURULDRURURRRDDDLURUUULLLRRRDDDLDRURDLUUURRUDLDDDLURULULLLDDL',
    'map13': 'UULDRDRDLUUUULLLLLLLDDDRULDRDDRDDRURRRRRULDLUU',
    'map14': 'RRRRULLDRRRDDDDLLLDRURRUUDDLLDRDRRLLULLURRRUUUULLLLLLURDLLLLLDDDRDR',
    'map15': 'RRRRUUUUUUURRRUURRRDRDUSLLLLSDULULLLDSLLLLLDLLDDDLDRURRRRRRR',
    'map16': 'RRRRRDRURLLLRRRRLLLLSLDRURRRR',
    'map17': (
        'DDDDDLURRRRRURRRLLLDLLLLUUUUUURRRRDRRRRDLURDURDLUURDLLURDLLLLULLLL'
        'DDDDDDRRRRURRRDDULULLLDLLLUUULURRRRRDRRR'
    ),
    'map18': 'ULDRRRRUUDDLLLURDLLURDRRRDDUULLLULDRULLDDDDRRLLUUUURRDLURDDLURDRURRRRRDDDLURDDLURDLUR',
    'map19': 'RRRRRRRRDRULLLLLLDRURRRRRDDDDDLLLLLDLURRRRRRULDLLLLLDDDDRRRLLLLLLUU',
    'map20': 'DLDRDLUURUULLLDLLURDDLDDLDURUURUURRRDLDLLLLDDDDDSULDSRRRRD',
}


@pytest.fixture(scope='module')
def maps():
    return json.loads(MAPS_PATH.read_text(encoding='utf-8'))


def test_thirty_five_levels_in_order(maps):
    assert list(maps) == [f'map{index:02}' for index in range(1, 36)]
    for index, data in enumerate(maps.values(), 1):
        assert data['name'] == f'Level {index:02}'


@pytest.mark.parametrize('map_id', SOLUTIONS)
def test_map_objects_and_solution(maps, map_id):
    data = maps[map_id]
    board = init_map(map_id)
    occupied = set()
    for tile in [*board.tile, *board.bridge]:
        positions = set(tile.get_positions())
        assert not occupied.intersection(positions), (map_id, tile)
        assert all(0 <= x < 17 and 0 <= y < 17 for x, y in positions)
        occupied.update(positions)
    assert len(board.tile) == len(data['floor']) + len(data['fragile']) + len(data['switch']) + 1
    assert len(board.bridge) == len(data['bridge'])
    assert len(board.switch) == len(data['switch'])
    for bridge in board.bridge:
        assert bridge.w > 0 and bridge.h > 0
        assert type(bridge.initial_open) is bool
    for switch in board.switch:
        assert len({link.bridge_id for link in switch.effects}) == len(switch.effects)

    initial = board.game_state
    assert initial.block.positions == (tuple(data['block_start']),)
    assert initial.open_bridges == {
        bridge_id for bridge_id, bridge in data['bridge'].items() if bridge['initial_open']
    }
    rules = GameRules(board)
    assert rules.is_valid(initial)
    state = initial
    moves = {'U': Move.UP, 'D': Move.DOWN, 'L': Move.LEFT, 'R': Move.RIGHT, 'S': Move.SWITCH}
    for step, symbol in enumerate(SOLUTIONS[map_id], 1):
        state = rules.apply_action(state, moves[symbol])
        assert state is not None, (map_id, step, symbol)
    assert rules.is_goal(state), map_id
    assert board.game_state is initial


@pytest.mark.parametrize('map_id', NEW_MAPS)
def test_new_map_is_valid_and_solvable(maps, map_id):
    """map21-35 have no hand-authored move string (SOLUTIONS); verify them
    structurally and confirm BFS can actually reach the goal instead."""
    data = maps[map_id]
    board = init_map(map_id)
    occupied = set()
    for tile in board.tile:
        positions = set(tile.get_positions())
        assert not occupied.intersection(positions), (map_id, tile)
        occupied.update(positions)
    assert len(board.tile) == len(data['floor']) + 1  # floor tiles + the Goal tile
    assert not data['bridge'] and not data['switch'] and not data['fragile']

    rules = GameRules(board)
    initial = board.game_state
    assert rules.is_valid(initial)
    assert not rules.is_goal(initial)

    solution = BFSSolver(rules).solve(initial)
    assert solution is not None, f'{map_id} has no BFS solution'
    state = initial
    for action in solution:
        state = rules.apply_action(state, action)
        assert state is not None
    assert rules.is_goal(state)
    assert board.game_state is initial


@pytest.mark.parametrize('map_name', ('map01', 'Level 01'))
def test_load_map_from_another_working_directory(map_name, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    board = init_map(map_name)
    assert board.game_state.block.positions == ((4, 6),)


def test_unknown_map_name():
    with pytest.raises(ValueError, match='Unknown map: missing'):
        init_map('missing')


def test_loads_create_independent_boards():
    first = init_map('map02')
    second = init_map('map02')
    first.tile.clear()
    first.bridge.clear()
    assert second.tile
    assert second.bridge
    assert first.game_state == second.game_state
