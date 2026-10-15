"""Check Board storage, lookup, and game-state initialization."""

import pytest

from BackEnd.logic.board import Board
from BackEnd.objects.blocks import BlockState, GameState, Orientation
from BackEnd.objects.bridges import Bridge
from BackEnd.objects.switchs import SoftSwitch
from BackEnd.objects.tiles import EmptyCell, FloorTile


def test_empty_board():
    board = Board()
    assert board.tile == board.switch == board.bridge == []
    assert board.block is board.game_state is None
    assert board.get_tile((2, 5)) is None
    assert board.get_switch('missing') is None
    assert board.get_bridge('missing') is None
    with pytest.raises(ValueError, match='Add a block'):
        board.initialize_game_state()


@pytest.mark.parametrize('method', ('add_tile', 'add_switch'))
def test_switch_registration_and_lookup(method):
    board = Board()
    switch = SoftSwitch(2, 5, 'soft')
    getattr(board, method)(switch)
    assert board.tile == board.switch == [switch]
    assert board.get_tile((2, 5)) is switch
    assert board.get_tile((5, 2)) is None
    assert board.get_switch('soft') is switch


@pytest.mark.parametrize('method', ('add_tile', 'add_bridge'))
def test_bridge_overlay_lookup(method):
    board = Board()
    board.add_tile(EmptyCell(2, 5))
    bridge = Bridge(2, 5, 2, 3, 'bridge')
    getattr(board, method)(bridge)
    for position in bridge.get_positions():
        assert board.get_tile(position) is bridge
    assert board.get_tile((4, 5)) is None
    assert board.get_bridge('bridge') is bridge


@pytest.mark.parametrize('use_start_position', (True, False))
def test_initial_state_and_reset(use_start_position):
    board = Board()
    board.add_tile(FloorTile(2, 5))
    board.add_bridge(Bridge(7, 9, 1, 1, 'open', True))
    board.add_bridge(Bridge(8, 9, 1, 1, 'closed'))
    block = BlockState(((2, 5),), Orientation.STANDING)
    if use_start_position:
        state = board.initialize_game_state((2, 5))
    else:
        board.add_block(block)
        state = board.initialize_game_state()
    assert state == GameState(block, {'open'})
    assert board.block is state.block
    assert board.game_state is state
    board.add_game_state(GameState(block, {'closed'}))
    assert board.initialize_game_state() == state


def test_adding_block_preserves_bridge_state():
    board = Board()
    initial = BlockState(((2, 5),), Orientation.STANDING)
    board.add_game_state(GameState(initial, {'bridge'}))
    moved = BlockState(((3, 5),), Orientation.STANDING)
    board.add_block(moved)
    assert board.game_state == GameState(moved, {'bridge'})
    assert board.block is moved


def test_initialize_split_block():
    board = Board()
    block = BlockState.split(((2, 5), (7, 9)), active_cube=1)
    board.add_block(block)
    state = board.initialize_game_state()
    assert state.block is board.block is block
    assert state.block.active_cube == 1
