import tracemalloc

import pytest

from BackEnd.init_map import init_map
from BackEnd.logic.board import Board
from BackEnd.logic.game_rules import GameRules
from BackEnd.objects.tiles import FloorTile, Goal
from BackEnd.Solver.DFSSolver import DFSSolver


@pytest.mark.parametrize("map_name", [f"map{i:02}" for i in range(1, 21)])
def test_dfs_solution_replays_on_original_board(map_name):
    board = init_map(map_name)
    initial = board.game_state
    rules = GameRules(board)
    result = DFSSolver(rules).solve(initial)
    assert result.status == "solved", result.message
    state = initial
    for action in result.actions:
        state = rules.apply_action(state, action)
        assert state is not None
    assert rules.is_goal(state)
    assert board.game_state == initial
    assert result.path_cost == len(result.actions)
    assert result.search_time_s >= 0
    assert result.peak_memory_bytes > 0
    assert not tracemalloc.is_tracing()


def test_already_solved_has_zero_cost_and_no_expansions():
    board = Board()
    board.add_tile(Goal(0, 0))
    result = DFSSolver(GameRules(board)).solve(board.initialize_game_state((0, 0)))
    assert result.status == "solved"
    assert result.actions == [] and result.path_cost == 0
    assert result.expanded_nodes == 0


def test_unreachable_goal_exhausts_cycle_without_revisiting():
    board = Board()
    for x in range(4):
        board.add_tile(FloorTile(x, 0))
    board.add_tile(Goal(10, 0))
    result = DFSSolver(GameRules(board)).solve(board.initialize_game_state((0, 0)))
    assert result.status == "no_solution"
    assert result.actions == [] and result.path_cost is None
    assert result.expanded_nodes == 3


def test_invalid_start_returns_error():
    board = init_map("map01")
    invalid = board.initialize_game_state((-100, -100))
    result = DFSSolver(GameRules(board)).solve(invalid)
    assert result.status == "error"
    assert result.expanded_nodes == 0


def test_existing_memory_measurement_is_preserved():
    board = init_map("map01")
    tracemalloc.start()
    try:
        result = DFSSolver(GameRules(board)).solve(board.game_state)
        assert result.status == "solved"
        assert result.peak_memory_bytes is None
        assert tracemalloc.is_tracing()
    finally:
        tracemalloc.stop()
