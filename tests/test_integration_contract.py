import pytest


def test_backend_exports_same_types_as_object_modules():
    from BackEnd import BlockState, Move, SoftSwitch
    from BackEnd.objects.blocks import BlockState as ModuleBlockState
    from BackEnd.objects.sharing import Move as ModuleMove
    from BackEnd.objects.switchs import SoftSwitch as ModuleSoftSwitch
    assert BlockState is ModuleBlockState
    assert Move is ModuleMove
    assert SoftSwitch is ModuleSoftSwitch


def test_unknown_bridge_is_rejected_when_constructing_board():
    from BackEnd import Board, EffectMode, FloorTile, SoftSwitch, SwitchBridgeLink
    with pytest.raises(ValueError, match='unknown bridge'):
        Board([[SoftSwitch(0, 0, 's', (SwitchBridgeLink('missing', EffectMode.TOGGLE),)),
                FloorTile(1, 0)]], {}, (0, 0), (0, 1))


def test_replay_from_start_through_bridge_split_merge_to_goal():
    """A GUI/solver client can replay a complete stage using only the public API."""
    from BackEnd import (
        Board, Bridge, EffectMode, FloorTile, FragileTile, GameRules, Goal,
        Move, Orientation, SoftSwitch, SplitSwitch, SwitchBridgeLink, initial_state,
    )
    grid = [[FloorTile(c, r) for c in range(7)] for r in range(5)]
    grid[2][1] = SoftSwitch(1, 2, 'open-crossing', (
        SwitchBridgeLink('crossing', EffectMode.SET, True),
    ))
    grid[2][4] = FragileTile(4, 2)
    grid[2][6] = SplitSwitch(6, 2, 'split', teleport_positions=((4, 4), (4, 1)))
    grid[4][4] = Goal(4, 4)
    board = Board(grid, {'crossing': Bridge(3, 2, 1, 1, 'crossing')}, (2, 0), (4, 4))
    rules = GameRules(board)
    start = initial_state(board)
    # Expected waypoints come from the stage route, not private transition helpers.
    waypoints = [
        (Move.RIGHT, ((2, 1), (2, 2)), Orientation.HORIZONTAL, 0),
        (Move.RIGHT, ((2, 3),), Orientation.STANDING, 0),
        (Move.RIGHT, ((2, 4), (2, 5)), Orientation.HORIZONTAL, 0),
        (Move.RIGHT, ((4, 1), (4, 4)), Orientation.SPLIT, 0),
        (Move.RIGHT, ((4, 2), (4, 4)), Orientation.SPLIT, 0),
        (Move.SWITCH, ((4, 2), (4, 4)), Orientation.SPLIT, 1),
        (Move.LEFT, ((4, 2), (4, 3)), Orientation.HORIZONTAL, 0),
        (Move.RIGHT, ((4, 4),), Orientation.STANDING, 0),
    ]
    current = start
    replay_log = {start: ()}
    for action, positions, orientation, active in waypoints:
        assert not rules.is_goal(current)
        assert action in rules.get_valid_actions(current)
        successor = rules.apply_action(current, action)
        assert successor is not None and rules.is_valid(successor)
        assert successor.block.positions == positions
        assert successor.block.orientation == orientation
        assert successor.block.active_cube == active
        assert successor.open_bridges == frozenset({'crossing'})
        replay_log[successor] = replay_log[current] + (action,)
        current = successor
    assert rules.is_goal(current)
    # A second consumer can replay the saved action path without hidden engine state.
    replay_rules = GameRules(board)
    replay = initial_state(board)
    for action in replay_log[current]:
        replay = replay_rules.apply_action(replay, action)
    assert replay == current
    assert start.open_bridges == frozenset()


def test_board_snapshots_input_containers():
    from BackEnd import Board, Bridge, EmptyCell, FloorTile, GameRules, Move, initial_state
    tiles = [[FloorTile(c, 0) for c in range(4)]]
    bridges = {'b': Bridge(3, 0, 1, 1, 'b', True)}
    board = Board(tiles, bridges, (0, 0), (0, 3))
    rules = GameRules(board)
    start = initial_state(board)
    expected = rules.apply_action(start, Move.RIGHT)
    tiles[0][1] = EmptyCell(1, 0)
    bridges.clear()
    assert rules.apply_action(start, Move.RIGHT) == expected
    with pytest.raises(TypeError):
        board.bridges['new'] = Bridge(2, 0, 1, 1, 'new')


@pytest.mark.parametrize('problem', ['duplicate-switch', 'bridge-key', 'overlap', 'coordinates'])
def test_ambiguous_stage_configuration_rejected(problem):
    from BackEnd import Board, Bridge, FloorTile, SoftSwitch
    tiles = [[FloorTile(c, 0) for c in range(4)]]
    bridges = {}
    if problem == 'duplicate-switch':
        tiles[0][1], tiles[0][2] = SoftSwitch(1, 0, 'same'), SoftSwitch(2, 0, 'same')
        message = 'unique'
    elif problem == 'bridge-key':
        bridges = {'wrong': Bridge(3, 0, 1, 1, 'b')}
        message = 'key'
    elif problem == 'overlap':
        bridges = {'a': Bridge(2, 0, 2, 1, 'a'), 'b': Bridge(3, 0, 1, 1, 'b')}
        message = 'overlap'
    else:
        tiles[0][1] = FloorTile(0, 1)
        message = 'coordinates'
    with pytest.raises(ValueError, match=message):
        Board(tiles, bridges, (0, 0), (0, 3))
