"""All solvers share real measurements, limits, and result semantics."""

import tracemalloc

import pytest

from BackEnd.Benchmark import Benchmark
from BackEnd.init_map import init_map
from BackEnd.logic.board import Board
from BackEnd.logic.game_rules import GameRules
from BackEnd.objects.tiles import FloorTile, Goal
from BackEnd.search import SOLVERS, solve


@pytest.mark.parametrize("algorithm", SOLVERS)
@pytest.mark.parametrize("map_id", ["map02", "map04", "map09"])
def test_benchmarked_solution_replays_without_mutating_board(algorithm, map_id):
    board = init_map(map_id)
    initial = board.game_state
    result = solve(board, initial, algorithm)
    assert result.status == "solved", result.message
    assert board.game_state is initial
    assert result.expanded_nodes > 0
    assert result.peak_memory_bytes > 0
    assert result.search_time_s > 0
    assert result.path_cost == len(result.actions)
    rules = GameRules(board)
    state = initial
    for action in result.actions:
        state = rules.apply_action(state, action)
        assert state is not None
    assert rules.is_goal(state)
    if algorithm != "DFS":
        assert result.path_cost == len(SOLVERS["BFS"](rules).solve(initial))


@pytest.mark.parametrize("algorithm", SOLVERS)
def test_expansion_count_and_terminal_cases(algorithm):
    board = Board()
    # Two RIGHT actions reach the goal, expanding just two states.
    for x in range(3):
        board.add_tile(FloorTile(x, 0))
    board.add_tile(Goal(3, 0))
    start = board.initialize_game_state((0, 0))
    result = solve(board, start, algorithm)
    assert result.status == "solved"
    assert result.expanded_nodes == 2
    assert result.path_cost == 2
    goal = board.initialize_game_state((3, 0))
    result = solve(board, goal, algorithm, max_nodes=0)
    assert result.status == "solved"
    assert result.expanded_nodes == result.path_cost == 0

    board = Board()
    board.add_tile(FloorTile(0, 0))
    board.add_tile(Goal(10, 0))
    start = board.initialize_game_state((0, 0))
    result = solve(board, start, algorithm)
    assert result.status == "no_solution"
    assert result.expanded_nodes == 1
    assert result.path_cost is None
    assert result.actions == []


@pytest.mark.parametrize("algorithm", SOLVERS)
def test_limits_are_distinct_from_no_solution(algorithm):
    board = init_map("map01")
    result = solve(board, board.game_state, algorithm, max_nodes=1)
    assert result.status == "limit"
    assert result.expanded_nodes == 1
    assert result.actions == []
    assert result.path_cost is None
    result = solve(board, board.game_state, algorithm, time_limit=0)
    assert result.status == "limit"
    assert result.expanded_nodes == 0


def test_benchmark_reuse_and_error_cleanup():
    board = init_map("map01")
    rules = GameRules(board)
    benchmark = Benchmark()
    first = benchmark.run(SOLVERS["BFS"], rules, board.game_state, "BFS")
    second = benchmark.run(SOLVERS["BFS"], rules, board.game_state, "BFS")
    assert first.expanded_nodes == second.expanded_nodes

    class BrokenSolver:
        def __init__(self, rules, benchmark):
            raise RuntimeError("test failure")

    owned_trace = tracemalloc.is_tracing()
    result = benchmark.run(BrokenSolver, rules, board.game_state, "broken")
    assert result.status == "error"
    assert "test failure" in result.message
    assert tracemalloc.is_tracing() == owned_trace
    assert solve(board, board.game_state, "unknown").status == "error"


def test_astar_preprocessing_checks_deadline(monkeypatch):
    ticks = iter([0, 0, 10, 10])
    monkeypatch.setattr("BackEnd.Benchmark.perf_counter", lambda: next(ticks))
    board = init_map("map01")
    result = solve(board, board.game_state, "A*", time_limit=1)
    assert result.status == "limit"
    assert result.expanded_nodes == 0
