"""Integration tests for UI state and actual solver replay."""
import pytest

from BackEnd.objects.sharing import Move
from BackEnd.search import solve
from FrontEnd.controller import GameController


@pytest.mark.parametrize("algorithm", ["BFS", "DFS", "UCS", "A*"])
def test_solver_replay_reaches_goal(algorithm):
    game = GameController()
    start = game.state
    result = solve(game.board, start, algorithm)
    assert result.status == "solved"
    assert game.state == start
    if algorithm != "DFS":
        assert len(result.actions) == 7
    game.set_solution(result, start)
    for _ in result.actions:
        game.step()
    assert game.status == "won"
    assert game.rules.is_goal(game.state)
    assert game.replay_index == len(result.actions)


def test_space_is_ignored_and_restart_resets_loss():
    game = GameController()
    start = game.state
    assert not game.move(Move.SWITCH)
    assert game.state == start and game.status == "playing"
    invalid = next(action for action in (Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT)
                   if game.rules.apply_action(start, action) is None)
    game.move(invalid)
    assert game.status == "lost"
    game.restart()
    assert game.status == "playing" and game.state == start


def test_advanced_level_replay_and_restart():
    game = GameController("map09")
    initial = game.state
    mapping = {"R": Move.RIGHT, "L": Move.LEFT, "U": Move.UP, "D": Move.DOWN, "S": Move.SWITCH}
    saw_split = False
    for char in "RDRRRRRRURDRRRRRUSDLLLLLD":
        assert game.move(mapping[char])
        saw_split |= game.state.block.is_split()
    assert saw_split and game.status == "won"
    game.restart()
    assert game.state == initial
    assert not game.history and not game.solution


def test_search_limit_is_not_reported_as_no_solution():
    game = GameController()
    assert solve(game.board, game.state, max_nodes=0).status == "limit"


def test_manual_move_discards_old_replay():
    game = GameController()
    result = solve(game.board, game.state)
    game.set_solution(result, game.state)
    assert game.move(result.actions[0])
    assert not game.solution and game.result is None
