"""Switch/block contract tests, independent of GUI and search implementations."""
from dataclasses import FrozenInstanceError

import pytest

from BackEnd import (
    BlockState, Bridge, EffectMode, EmptyCell, FloorTile, FragileTile,
    GameState, Goal, HeavySwitch, Orientation, SoftSwitch, SplitSwitch, SwitchBridgeLink,
)
from BackEnd import Board, GameRules, Move, initial_state

S, H, V, P = Orientation.STANDING, Orientation.HORIZONTAL, Orientation.VERTICAL, Orientation.SPLIT


# A real, initially closed bridge is present for switch-effect scenarios.
TEST_BRIDGES = (Bridge(9, 9, 1, 1, 'b'),)


def board(*tiles, bridges=TEST_BRIDGES):
    grid = [[FloorTile(c, r) for c in range(10)] for r in range(10)]
    grid[8][8] = Goal(8, 8)
    for tile in tiles:
        grid[tile.y][tile.x] = tile
    return Board(grid, {b.bridge_id: b for b in bridges}, (4, 4), (8, 8))


def state(positions=((4, 4),), orientation=S, active=0, opened=()):
    return GameState(BlockState(positions, orientation, active), frozenset(opened))


def link(mode=EffectMode.TOGGLE, target=None):
    return (SwitchBridgeLink('b', mode, target),)


@pytest.mark.parametrize('orientation,positions,move,expected,expected_orientation', [
    (S, ((4, 4),), Move.UP, ((2, 4), (3, 4)), V),
    (S, ((4, 4),), Move.DOWN, ((5, 4), (6, 4)), V),
    (S, ((4, 4),), Move.LEFT, ((4, 2), (4, 3)), H),
    (S, ((4, 4),), Move.RIGHT, ((4, 5), (4, 6)), H),
    (H, ((4, 4), (4, 5)), Move.UP, ((3, 4), (3, 5)), H),
    (H, ((4, 4), (4, 5)), Move.DOWN, ((5, 4), (5, 5)), H),
    (H, ((4, 4), (4, 5)), Move.LEFT, ((4, 3),), S),
    (H, ((4, 4), (4, 5)), Move.RIGHT, ((4, 6),), S),
    (V, ((4, 4), (5, 4)), Move.UP, ((3, 4),), S),
    (V, ((4, 4), (5, 4)), Move.DOWN, ((6, 4),), S),
    (V, ((4, 4), (5, 4)), Move.LEFT, ((4, 3), (5, 3)), V),
    (V, ((4, 4), (5, 4)), Move.RIGHT, ((4, 5), (5, 5)), V),
])
def test_roll_table(orientation, positions, move, expected, expected_orientation):
    rules = GameRules(board())
    before = state(positions, orientation)
    assert rules.apply_action(before, move) == state(expected, expected_orientation)


@pytest.mark.parametrize('tile', [EmptyCell(6, 4), FragileTile(6, 4)])
def test_illegal_landing(tile):
    assert GameRules(board(tile)).apply_action(state(((4, 4), (4, 5)), H), Move.RIGHT) is None


def test_outside_and_cube_collision():
    rules = GameRules(board())
    assert rules.apply_action(state(((0, 0),)), Move.UP) is None
    assert rules.apply_action(state(((4, 4), (4, 5)), P), Move.RIGHT) is None


@pytest.mark.parametrize('orientation,positions', [(S, ((4, 4),)), (P, ((4, 5), (8, 8)))])
def test_fragile_supports_lying_and_cube(orientation, positions):
    result = GameRules(board(FragileTile(6, 4))).apply_action(
        state(positions, orientation), Move.RIGHT)
    assert result is not None
    assert result.block.occupies((4, 6))


@pytest.mark.parametrize('switch_class,orientation,positions,activated', [
    (SoftSwitch, H, ((4, 4), (4, 5)), True),
    (SoftSwitch, S, ((4, 4),), True),
    (SoftSwitch, P, ((4, 5), (8, 8)), True),
    (HeavySwitch, H, ((4, 4), (4, 5)), True),
    (HeavySwitch, S, ((4, 4),), False),
    (HeavySwitch, P, ((4, 5), (8, 8)), False),
])
def test_switch_activation(switch_class, orientation, positions, activated):
    rules = GameRules(board(switch_class(6, 4, 's', link()), bridges=(Bridge(0, 0, 1, 1, 'b'),)))
    result = rules.apply_action(state(positions, orientation), Move.RIGHT)
    assert result is not None
    assert ('b' in result.open_bridges) == activated


def test_stationary_cube_and_switch_action_do_not_retrigger():
    rules = GameRules(board(SoftSwitch(2, 2, 's', link())))
    before = state(((2, 2), (6, 6)), P, active=1, opened=('b',))
    assert rules.apply_action(before, Move.RIGHT).open_bridges == before.open_bridges
    swapped = rules.apply_action(before, Move.SWITCH)
    assert swapped.block.active_cube == 0
    assert swapped.open_bridges == before.open_bridges
    assert rules.apply_action(state(), Move.SWITCH) is None


@pytest.mark.parametrize('mode,target,initial,after_once,after_twice', [
    (EffectMode.TOGGLE, None, (), {'b'}, set()),
    (EffectMode.SET, True, (), {'b'}, {'b'}),
    (EffectMode.SET, False, ('b',), set(), set()),
])
def test_repeated_effects(mode, target, initial, after_once, after_twice):
    rules = GameRules(board(SoftSwitch(3, 2, 's', link(mode, target))))
    before = state(((2, 2), (8, 8)), P, opened=initial)
    first = rules.apply_action(before, Move.RIGHT)
    assert first.open_bridges == after_once
    away = rules.apply_action(first, Move.LEFT)
    second = rules.apply_action(away, Move.RIGHT)
    assert second.open_bridges == after_twice


def test_bridge_overlay_and_initial_state():
    b = board(EmptyCell(2, 3), bridges=(Bridge(2, 3, 2, 2, 'b', True), Bridge(7, 7, 1, 1, 'closed')))
    rules = GameRules(b)
    assert initial_state(b) == state(opened=('b',))
    assert b.bridges['b'].get_positions() == ((3, 2), (3, 3), (4, 2), (4, 3))
    for position in b.bridges['b'].get_positions():
        assert rules.is_valid(state((position,), opened=('b',)))
        assert not rules.is_valid(state((position,)))
    assert FloorTile(2, 3).get_positions() == ((3, 2),)


def test_close_bridge_under_other_end():
    rules = GameRules(board(SoftSwitch(5, 4, 's', link()), bridges=(Bridge(6, 4, 1, 1, 'b'),)))
    assert rules.apply_action(state(opened=('b',)), Move.RIGHT) is None


def test_closed_bridge_cannot_be_opened_by_same_landing():
    rules = GameRules(board(SoftSwitch(5, 4, 's', link()), bridges=(Bridge(6, 4, 1, 1, 'b'),)))
    assert rules.apply_action(state(), Move.RIGHT) is None


def test_close_bridge_under_stationary_cube():
    rules = GameRules(board(SoftSwitch(3, 2, 's', link()), bridges=(Bridge(6, 6, 1, 1, 'b'),)))
    assert rules.apply_action(state(((2, 2), (6, 6)), P, opened=('b',)), Move.RIGHT) is None


def test_multiple_switches_are_ordered_by_id():
    rules = GameRules(board(SoftSwitch(5, 4, 'z', link()), SoftSwitch(6, 4, 'a', link(EffectMode.SET, True))))
    assert rules.apply_action(state(), Move.RIGHT).open_bridges == frozenset()


def split_board(*extra, positions=((7, 7), (2, 2)), effects=(), bridges=TEST_BRIDGES):
    return board(SplitSwitch(6, 4, 'split', effects, teleport_positions=positions), *extra, bridges=bridges)


def test_split_teleport_effects_no_cascade_and_switch():
    rules = GameRules(split_board(SoftSwitch(2, 2, 'destination', link()), effects=link(EffectMode.SET, True)))
    result = rules.apply_action(state(((4, 4), (4, 5)), H), Move.RIGHT)
    assert result == state(((2, 2), (7, 7)), P, opened=('b',))
    assert rules.apply_action(result, Move.SWITCH) == state(((2, 2), (7, 7)), P, 1, ('b',))


@pytest.mark.parametrize('positions', [((2, 2), (2, 2)), ((2, 2), (2, 3)), ((2, 2), (3, 2))])
def test_bad_teleport_level_rejected(positions):
    with pytest.raises(ValueError, match='distinct and non-adjacent'):
        split_board(positions=positions)


@pytest.mark.parametrize('tile,opened', [(EmptyCell(2, 2), ()), (Bridge(2, 2, 1, 1, 'b'), ())])
def test_unsupported_teleport_rejected(tile, opened):
    b = split_board(tile) if isinstance(tile, EmptyCell) else split_board(bridges=(tile,))
    assert GameRules(b).apply_action(state(((4, 4), (4, 5)), H, opened=opened), Move.RIGHT) is None


def test_teleport_support_checked_after_effects():
    rules = GameRules(split_board(effects=link(EffectMode.SET, True), bridges=(Bridge(2, 2, 1, 1, 'b'),)))
    assert rules.apply_action(state(((4, 4), (4, 5)), H), Move.RIGHT) is not None


def test_canonical_split_hash_and_active_cube_tracks_motion():
    a = BlockState.split(((2, 2), (7, 7)), 0)
    b = BlockState.split(((7, 7), (2, 2)), 1)
    assert a == b and hash(a) == hash(b)
    assert state(((7, 7), (2, 2)), P, 1) == state(((2, 2), (7, 7)), P)
    rules = GameRules(board(SoftSwitch(5, 3, 's', link())))
    # Moving cube changes its sorted index; the switch still sees that cube's landing.
    result = rules.apply_action(state(((2, 5), (3, 1)), P), Move.DOWN)
    assert result == state(((3, 1), (3, 5)), P, 1, ('b',))


@pytest.mark.parametrize('positions,move,orientation,expected', [
    (((4, 2), (4, 4)), Move.RIGHT, H, ((4, 3), (4, 4))),
    (((2, 4), (4, 4)), Move.DOWN, V, ((3, 4), (4, 4))),
    (((4, 2), (4, 5)), Move.RIGHT, P, ((4, 3), (4, 5))),
])
def test_merge(positions, move, orientation, expected):
    assert GameRules(board()).apply_action(state(positions, P), move) == state(expected, orientation)


def test_merge_does_not_activate_heavy_switch():
    rules = GameRules(board(HeavySwitch(3, 4, 's', link())))
    result = rules.apply_action(state(((4, 2), (4, 4)), P), Move.RIGHT)
    assert result == state(((4, 3), (4, 4)), H)


@pytest.mark.parametrize('orientation,positions', [(P, ((4, 5), (8, 8))), (S, ((4, 4),))])
def test_cube_or_lying_block_does_not_activate_split(orientation, positions):
    result = GameRules(split_board()).apply_action(state(positions, orientation), Move.RIGHT)
    assert result.block.positions != ((2, 2), (7, 7))
    assert result.block.orientation == (P if orientation == P else H)


@pytest.mark.parametrize('positions,orientation,won', [
    (((8, 8),), S, True), (((8, 7), (8, 8)), H, False),
    (((7, 8), (8, 8)), V, False), (((2, 2), (8, 8)), P, False),
    (((4, 4),), S, False),
])
def test_goal(positions, orientation, won):
    assert GameRules(board(Goal(8, 8))).is_goal(state(positions, orientation)) is won


def test_purity_hashability_and_valid_actions():
    rules = GameRules(board(SoftSwitch(5, 4, 's', link())))
    before = state()
    old_hash = hash(before)
    assert rules.apply_action(before, Move.RIGHT) == rules.apply_action(before, Move.RIGHT)
    assert hash(before) == old_hash and before.open_bridges == frozenset()
    with pytest.raises(FrozenInstanceError):
        before.block.active_cube = 1
    with pytest.raises(FrozenInstanceError):
        before.open_bridges = frozenset({'b'})
    assert rules.get_valid_actions(state(((0, 0),))) == [Move.RIGHT, Move.DOWN]
    split = state(((0, 0), (8, 8)), P)
    assert rules.get_valid_actions(split) == [Move.RIGHT, Move.DOWN, Move.SWITCH]
    with pytest.raises(TypeError, match='Move'):
        rules.apply_action(before, 'RIGHT')


def test_set_requires_boolean_target():
    with pytest.raises(ValueError, match='target_open'):
        SwitchBridgeLink('b', EffectMode.SET)
