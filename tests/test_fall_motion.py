import math

import pytest

from BackEnd.logic.board import Board
from BackEnd.logic.game_rules import GameRules
from BackEnd.objects.blocks import BlockState, GameState, Orientation
from BackEnd.objects.sharing import Move
from BackEnd.objects.tiles import FloorTile, FragileTile
from FrontEnd.fall_motion import fall_vertex, prepare_fall


@pytest.mark.parametrize('axis', [0, 1])
@pytest.mark.parametrize('sign', [-1, 1])
def test_tipping_keeps_supported_side_above_floor(axis, sign):
    plan = {'edge': (axis, sign, 0)}
    # Sample the entire volume, including face interiors, across the tip.
    for frame in range(37):
        for q in (-1, -.5, 0, .5, 1):
            for z in (0, .5, 1):
                v = (q, .5, z) if axis == 0 else (.5, q, z)
                moved = fall_vertex(v, plan, frame / 100)
                if sign * moved[axis] < -1e-8:
                    assert moved[2] >= -1e-8
    # Once detached, it stays beyond the supporting edge.
    for q in (-1, 0, 1):
        v = (q, .5, .035) if axis == 0 else (.5, q, .035)
        assert sign * fall_vertex(v, plan, .5)[axis] > 0


def test_landing_support_selects_edge_not_original_roll_pivot():
    board = Board()
    board.add_tile(FloorTile(0, 0))
    board.add_tile(FloorTile(1, 0))
    before = board.initialize_game_state((0, 0))
    rules = GameRules(board)
    assert rules.apply_action(before, Move.RIGHT) is None
    plan = prepare_fall(rules, before, Move.RIGHT)
    assert plan['edge'] == (0, 1, 2)
    assert plan['supported'] == [(1, 0)]
    assert board.game_state == before


def test_fragile_landing_opens_hole_and_drops_in_place():
    board = Board()
    for x in (0, 1):
        board.add_tile(FloorTile(x, 0))
    board.add_tile(FragileTile(2, 0))
    before = GameState(BlockState(((0, 0), (1, 0)), Orientation.HORIZONTAL))
    plan = prepare_fall(GameRules(board), before, Move.RIGHT)
    assert plan['broken'] == [(2, 0)]
    assert plan['edge'] is None
    assert fall_vertex((2.5, .5, 1), plan, .3) == pytest.approx((2.5, .5, -.35))
