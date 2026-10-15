"""Game-rule behavior for movement, switches, bridges, and split cubes."""

import pytest

from BackEnd.logic.board import Board
from BackEnd.logic.game_rules import GameRules
from BackEnd.objects.blocks import BlockState, GameState, Orientation
from BackEnd.objects.bridges import Bridge
from BackEnd.objects.sharing import Move
from BackEnd.objects.switchs import (
    EffectMode, HeavySwitch, SoftSwitch, SplitSwitch, SwitchBridgeLink,
)
from BackEnd.objects.tiles import EmptyCell, FloorTile, FragileTile, Goal


def make_board(*tiles, bridges=()):
    overrides = {(tile.x, tile.y): tile for tile in tiles}
    board = Board()
    for x in range(10):
        for y in range(10):
            board.add_tile(overrides.get((x, y), FloorTile(x, y)))
    for bridge in bridges:
        board.add_bridge(bridge)
    return board


def state(positions=((4, 4),), orientation=Orientation.STANDING, active=0, opened=()):
    return GameState(BlockState(positions, orientation, active), frozenset(opened))


def effect(mode=EffectMode.TOGGLE, target=None):
    return (SwitchBridgeLink('bridge', mode, target),)


@pytest.mark.parametrize('orientation,positions,move,expected,result_orientation', (
    (Orientation.STANDING, ((4, 4),), Move.UP, ((4, 2), (4, 3)), Orientation.VERTICAL),
    (Orientation.STANDING, ((4, 4),), Move.DOWN, ((4, 5), (4, 6)), Orientation.VERTICAL),
    (Orientation.STANDING, ((4, 4),), Move.LEFT, ((2, 4), (3, 4)), Orientation.HORIZONTAL),
    (Orientation.STANDING, ((4, 4),), Move.RIGHT, ((5, 4), (6, 4)), Orientation.HORIZONTAL),
    (Orientation.HORIZONTAL, ((4, 4), (5, 4)), Move.UP, ((4, 3), (5, 3)), Orientation.HORIZONTAL),
    (Orientation.HORIZONTAL, ((4, 4), (5, 4)), Move.DOWN, ((4, 5), (5, 5)), Orientation.HORIZONTAL),
    (Orientation.HORIZONTAL, ((4, 4), (5, 4)), Move.LEFT, ((3, 4),), Orientation.STANDING),
    (Orientation.HORIZONTAL, ((4, 4), (5, 4)), Move.RIGHT, ((6, 4),), Orientation.STANDING),
    (Orientation.VERTICAL, ((4, 4), (4, 5)), Move.UP, ((4, 3),), Orientation.STANDING),
    (Orientation.VERTICAL, ((4, 4), (4, 5)), Move.DOWN, ((4, 6),), Orientation.STANDING),
    (Orientation.VERTICAL, ((4, 4), (4, 5)), Move.LEFT, ((3, 4), (3, 5)), Orientation.VERTICAL),
    (Orientation.VERTICAL, ((4, 4), (4, 5)), Move.RIGHT, ((5, 4), (5, 5)), Orientation.VERTICAL),
))
def test_roll_transitions(orientation, positions, move, expected, result_orientation):
    rules = GameRules(make_board())
    assert rules.apply_action(state(positions, orientation), move) == state(expected, result_orientation)


@pytest.mark.parametrize('tile', (EmptyCell(6, 4), FragileTile(6, 4)))
def test_illegal_standing_landing(tile):
    rules = GameRules(make_board(tile))
    before = state(((4, 4), (5, 4)), Orientation.HORIZONTAL)
    assert rules.apply_action(before, Move.RIGHT) is None


def test_boundary_actions_and_wrong_action_type():
    rules = GameRules(make_board())
    before = state(((0, 0),))
    assert rules.get_valid_actions(before) == [Move.DOWN, Move.RIGHT]
    assert rules.apply_action(before, Move.SWITCH) is None
    with pytest.raises(TypeError, match='Move'):
        rules.apply_action(before, 'right')


@pytest.mark.parametrize('before', (
    state((), Orientation.STANDING),
    state(((1, 1), (2, 1)), Orientation.STANDING),
    state(((1, 1), (3, 1)), Orientation.HORIZONTAL),
    state(((1, 1), (2, 1)), Orientation.VERTICAL),
    state(((1, 1), (1, 1)), Orientation.SPLIT),
    state(((99, 99),)),
    state(opened=('unknown',)),
))
def test_invalid_states(before):
    rules = GameRules(make_board())
    assert not rules.is_valid(before)
    assert rules.get_valid_actions(before) == []
    assert not rules.is_goal(before)


@pytest.mark.parametrize('switch_class', (SoftSwitch, HeavySwitch))
@pytest.mark.parametrize('before,standing', (
    (state(((4, 4), (5, 4)), Orientation.HORIZONTAL), True),
    (state(), False),
    (state(((5, 4), (8, 8)), Orientation.SPLIT), False),
))
def test_soft_and_heavy_activation(switch_class, before, standing):
    board = make_board(switch_class(6, 4, 'switch', effect()),
                       bridges=(Bridge(9, 9, 1, 1, 'bridge'),))
    after = GameRules(board).apply_action(before, Move.RIGHT)
    assert after is not None
    assert ('bridge' in after.open_bridges) == (switch_class is SoftSwitch or standing)


@pytest.mark.parametrize('mode,target,opened,once,twice', (
    (EffectMode.TOGGLE, None, (), {'bridge'}, set()),
    (EffectMode.SET, True, (), {'bridge'}, {'bridge'}),
    (EffectMode.SET, False, ('bridge',), set(), set()),
))
def test_repeated_switch_effects(mode, target, opened, once, twice):
    board = make_board(SoftSwitch(3, 2, 'soft', effect(mode, target)),
                       bridges=(Bridge(9, 9, 1, 1, 'bridge'),))
    rules = GameRules(board)
    before = state(((2, 2), (8, 8)), Orientation.SPLIT, opened=opened)
    first = rules.apply_action(before, Move.RIGHT)
    assert first.open_bridges == once
    away = rules.apply_action(first, Move.LEFT)
    second = rules.apply_action(away, Move.RIGHT)
    assert second.open_bridges == twice


def test_stationary_cube_and_switch_action_do_not_trigger_switch():
    board = make_board(SoftSwitch(2, 2, 'soft', effect()),
                       bridges=(Bridge(9, 9, 1, 1, 'bridge'),))
    rules = GameRules(board)
    before = state(((2, 2), (6, 6)), Orientation.SPLIT, active=1)
    assert rules.apply_action(before, Move.RIGHT).open_bridges == frozenset()
    swapped = rules.apply_action(before, Move.SWITCH)
    assert swapped.block.active_cube == 0
    assert swapped.block.positions == before.block.positions
    assert swapped.open_bridges == before.open_bridges


def test_switch_after_cube_order_changes():
    board = make_board(SoftSwitch(4, 1, 'stationary', effect()),
                       SoftSwitch(4, 3, 'landed', effect()),
                       bridges=(Bridge(9, 9, 1, 1, 'bridge'),))
    before = state(((3, 3), (4, 1)), Orientation.SPLIT)
    after = GameRules(board).apply_action(before, Move.RIGHT)
    assert after == state(((4, 1), (4, 3)), Orientation.SPLIT, active=1, opened=('bridge',))


def test_switch_order_is_deterministic():
    board = make_board(SoftSwitch(5, 4, 'z', effect()),
                       SoftSwitch(6, 4, 'a', effect(EffectMode.SET, True)),
                       bridges=(Bridge(9, 9, 1, 1, 'bridge'),))
    assert GameRules(board).apply_action(state(), Move.RIGHT).open_bridges == frozenset()


@pytest.mark.parametrize('before,bridge,switch', (
    (state(opened=('bridge',)), Bridge(6, 4, 1, 1, 'bridge'), SoftSwitch(5, 4, 'soft', effect())),
    (state(((2, 2), (6, 6)), Orientation.SPLIT, opened=('bridge',)),
     Bridge(6, 6, 1, 1, 'bridge'), SoftSwitch(3, 2, 'soft', effect())),
))
def test_closing_bridge_drops_block_or_stationary_cube(before, bridge, switch):
    rules = GameRules(make_board(switch, bridges=(bridge,)))
    assert rules.apply_action(before, Move.RIGHT) is None


def test_closed_bridge_cannot_be_opened_by_same_landing():
    board = make_board(SoftSwitch(5, 4, 'soft', effect()),
                       bridges=(Bridge(6, 4, 1, 1, 'bridge'),))
    assert GameRules(board).apply_action(state(), Move.RIGHT) is None


def test_split_teleport_chooses_cube_zero_and_does_not_trigger_destinations():
    split = SplitSwitch(6, 4, 'split', teleport_positions=((7, 7), (2, 2)))
    board = make_board(split, SoftSwitch(2, 2, 'destination', effect()),
                       bridges=(Bridge(9, 9, 1, 1, 'bridge'),))
    rules = GameRules(board)
    before = state(((4, 4), (5, 4)), Orientation.HORIZONTAL)
    assert rules.apply_action(before, Move.RIGHT) == state(((2, 2), (7, 7)), Orientation.SPLIT)
    cube = state(((5, 4), (8, 8)), Orientation.SPLIT)
    assert rules.apply_action(cube, Move.RIGHT) == state(((6, 4), (8, 8)), Orientation.SPLIT)


@pytest.mark.parametrize('opened', ((), ('bridge',)))
def test_split_effects_apply_before_destination_support_check(opened):
    split = SplitSwitch(6, 4, 'split', effect(), teleport_positions=((7, 7), (2, 2)))
    board = make_board(split, bridges=(Bridge(2, 2, 1, 1, 'bridge'),))
    before = state(((4, 4), (5, 4)), Orientation.HORIZONTAL, opened=opened)
    after = GameRules(board).apply_action(before, Move.RIGHT)
    if opened:
        assert after is None
    else:
        assert after == state(((2, 2), (7, 7)), Orientation.SPLIT, opened=('bridge',))


def test_switch_action_does_not_merge_adjacent_cubes():
    before = state(((2, 2), (3, 2)), Orientation.SPLIT)
    after = GameRules(make_board()).apply_action(before, Move.SWITCH)
    assert after == state(((2, 2), (3, 2)), Orientation.SPLIT, active=1)


@pytest.mark.parametrize('positions,move,expected,orientation', (
    (((2, 2), (4, 2)), Move.RIGHT, ((3, 2), (4, 2)), Orientation.HORIZONTAL),
    (((2, 2), (2, 4)), Move.DOWN, ((2, 3), (2, 4)), Orientation.VERTICAL),
    (((2, 2), (5, 2)), Move.RIGHT, ((3, 2), (5, 2)), Orientation.SPLIT),
))
def test_cube_merge(positions, move, expected, orientation):
    before = state(positions, Orientation.SPLIT)
    assert GameRules(make_board()).apply_action(before, move) == state(expected, orientation)


def test_cube_collision_is_illegal():
    before = state(((2, 2), (3, 2)), Orientation.SPLIT)
    assert GameRules(make_board()).apply_action(before, Move.RIGHT) is None


def test_fragile_supports_split_cubes_and_lying_blocks():
    rules = GameRules(make_board(FragileTile(6, 4)))
    assert rules.apply_action(state(), Move.RIGHT) is not None
    before = state(((5, 4), (8, 8)), Orientation.SPLIT)
    assert rules.apply_action(before, Move.RIGHT) is not None


def test_goal_requires_standing_block():
    rules = GameRules(make_board(Goal(8, 8)))
    assert rules.is_goal(state(((8, 8),)))
    assert not rules.is_goal(state(((7, 8), (8, 8)), Orientation.HORIZONTAL))
    assert not rules.is_goal(state(((2, 2), (8, 8)), Orientation.SPLIT))


def test_transitions_do_not_mutate_board_or_input_state():
    board = make_board()
    before = board.initialize_game_state((4, 4))
    rules = GameRules(board)
    after = rules.apply_action(before, Move.RIGHT)
    assert after == rules.apply_action(before, Move.RIGHT)
    assert board.game_state is before
    assert board.block is before.block
    assert before == state()


@pytest.mark.parametrize('positions', (
    ((2, 2),), ((2, 2), (2, 2)), ((2, 2), (3, 2)), ((2, 2), (99, 99)),
))
def test_invalid_teleport_configuration(positions):
    switch = SplitSwitch(6, 4, 'split', teleport_positions=positions)
    with pytest.raises(ValueError, match='[Tt]eleport'):
        GameRules(make_board(switch))


def test_unknown_bridge_effect_is_configuration_error():
    with pytest.raises(ValueError, match='unknown bridge'):
        GameRules(make_board(SoftSwitch(6, 4, 'soft', effect())))
