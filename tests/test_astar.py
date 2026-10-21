"""Replay A* solutions on existing maps with different game mechanics."""

import pytest
from collections import deque

from BackEnd.init_map import init_map
from BackEnd.logic.game_rules import GameRules
from BackEnd.objects.sharing import Move
from BackEnd.Solver.AStarSolver import AStarSolver


@pytest.mark.parametrize('map_id,expect_split,expect_bridge_change', [
    pytest.param('map01', False, False, id='basic'),
    pytest.param('map02', False, True, id='switches-and-bridges'),
    pytest.param('map04', False, False, id='fragile-tiles'),
    pytest.param('map08', True, False, id='split-and-merge'),
    pytest.param('map09', True, False, id='split-with-cube-switching'),
])
def test_astar_solves_existing_map(map_id, expect_split, expect_bridge_change):
    board = init_map(map_id)
    rules = GameRules(board)
    initial = board.game_state

    actions = AStarSolver(rules).solve(initial)

    assert actions is not None, f'{map_id}: no solution found'
    assert board.game_state is initial
    assert board.block == initial.block

    state = initial
    saw_split = False
    saw_bridge_change = False
    for step, action in enumerate(actions, 1):
        assert isinstance(action, Move)
        next_state = rules.apply_action(state, action)
        assert next_state is not None, (map_id, step, action)
        assert rules.is_valid(next_state), (map_id, step, action)
        saw_split |= next_state.block.is_split()
        saw_bridge_change |= next_state.open_bridges != state.open_bridges
        state = next_state

    assert rules.is_goal(state), map_id
    assert saw_split == expect_split
    assert saw_bridge_change == expect_bridge_change


@pytest.mark.parametrize('map_id', ['map01', 'map02', 'map04', 'map08', 'map09'])
def test_astar_heuristic_and_shortest_path_match_bfs(map_id):
    board = init_map(map_id)
    rules = GameRules(board)
    initial = board.game_state
    solver = AStarSolver(rules)
    queue = deque([(initial, 0)])
    visited = {initial}

    while queue:
        state, cost = queue.popleft()
        if rules.is_goal(state):
            shortest_cost = cost
            break
        for action in Move:
            next_state = rules.apply_action(state, action)
            if next_state is None:
                continue
            assert solver._heuristic_function(state) <= 1 + solver._heuristic_function(next_state)
            if next_state not in visited:
                visited.add(next_state)
                queue.append((next_state, cost + 1))
    else:
        pytest.fail(f'{map_id}: BFS found no solution')

    actions = solver.solve(initial)
    assert actions is not None
    assert len(actions) == shortest_cost
    state = initial
    for step, action in enumerate(actions):
        assert solver._heuristic_function(state) <= shortest_cost - step
        state = rules.apply_action(state, action)
    assert solver._heuristic_function(state) == 0
