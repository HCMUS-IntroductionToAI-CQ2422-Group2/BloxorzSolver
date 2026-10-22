"""Check UCS optimality, replay, and priority-queue edge cases."""

from collections import deque

import pytest

from BackEnd.Solver.UCSSolver import UCSSolver
from BackEnd.init_map import init_map
from BackEnd.logic.board import Board
from BackEnd.logic.game_rules import GameRules
from BackEnd.objects.blocks import BlockState, GameState, Orientation
from BackEnd.objects.sharing import Move
from BackEnd.objects.tiles import FloorTile, Goal


def bfs_distance(rules, initial):
    queue = deque([(initial, 0)])
    visited = {initial}
    while queue:
        state, distance = queue.popleft()
        if rules.is_goal(state):
            return distance
        for action in Move:
            successor = rules.apply_action(state, action)
            if successor is not None and successor not in visited:
                visited.add(successor)
                queue.append((successor, distance + 1))
    return None


@pytest.mark.parametrize('map_id,expect_split,expect_bridge_change', [
    pytest.param('map01', False, False, id='basic'),
    pytest.param('map02', False, True, id='switches-and-bridges'),
    pytest.param('map04', False, False, id='fragile-tiles'),
    pytest.param('map08', True, False, id='split-and-merge'),
    pytest.param('map09', True, False, id='split-with-cube-switching'),
])
def test_ucs_optimal_solution_replays(map_id, expect_split, expect_bridge_change):
    board = init_map(map_id)
    rules = GameRules(board)
    initial = board.game_state
    solver = UCSSolver(rules)

    actions = solver.solve(initial)

    assert actions is not None
    assert len(actions) == bfs_distance(rules, initial)
    assert board.game_state is initial
    assert board.block is initial.block
    assert solver.solve(initial) == actions

    state = initial
    saw_split = saw_bridge_change = False
    for action in actions:
        assert isinstance(action, Move)
        successor = rules.apply_action(state, action)
        assert successor is not None
        assert rules.is_valid(successor)
        saw_split |= successor.block.is_split()
        saw_bridge_change |= successor.open_bridges != state.open_bridges
        state = successor
    assert rules.is_goal(state)
    assert saw_split == expect_split
    assert saw_bridge_change == expect_bridge_change
    if map_id == 'map09':
        assert Move.SWITCH in actions
    assert solver.solve(state) == []


def test_ucs_exhausts_cycles_when_goal_is_unreachable():
    board = Board()
    for x in range(4):
        for y in range(4):
            board.add_tile(FloorTile(x, y))
    board.add_tile(Goal(10, 10))
    initial = board.initialize_game_state((0, 0))
    rules = GameRules(board)

    assert rules.get_valid_actions(initial)
    assert UCSSolver(rules).solve(initial) is None
    assert board.game_state is initial


@pytest.mark.parametrize('reachable_goal', [True, False])
def test_ucs_improves_cost_and_skips_stale_entries(reachable_goal):
    # Synthetic weighted edges distinguish UCS from FIFO search and exercise
    # replacement entries; production BaseSolver successors all have cost 1.
    board = Board()
    for x in range(4):
        board.add_tile(Goal(x, 0) if x == 3 else FloorTile(x, 0))
    states = [
        GameState(BlockState(((x, 0),), Orientation.STANDING))
        for x in range(4)
    ]
    start, expensive, detour, goal = states
    edges = {
        start: [(Move.RIGHT, expensive, 5), (Move.DOWN, detour, 1)],
        detour: [(Move.UP, expensive, 1)],
        expensive: [(Move.RIGHT, goal, 10)] if reachable_goal else [],
    }
    expanded = []

    class WeightedSolver(UCSSolver):
        def successors(self, state):
            expanded.append(state)
            yield from edges.get(state, [])

    actions = WeightedSolver(GameRules(board)).solve(start)

    expected = [Move.DOWN, Move.UP, Move.RIGHT] if reachable_goal else None
    assert actions == expected
    assert expanded == [start, detour, expensive]
