"""Exercise the real Pygame event loop and Windows-compatible worker lifecycle."""
import time

import pytest


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    pygame = pytest.importorskip("pygame")
    from FrontEnd.app import App
    instance = App(progress_path=tmp_path / "progress.json")
    yield instance
    instance.cancel_search()
    pygame.quit()


def test_solver_is_placeholder_and_panels_render(app):
    app.start_search("BFS")
    assert app.worker is None
    assert app.game.result is None
    app.toggle_panel("solver")
    app.draw()
    assert app.panel == "solver"
    app.toggle_panel("menu")
    app.draw()
    app.select_stage("map09")
    assert app.panel is None
    for name in app.levels:
        app.progress.records[name] = {"stars": 3, "moves": 1}
    for name in app.levels:
        app.load_level(name)
        app.draw()


def test_modal_blocks_movement(app):
    import pygame
    before = app.game.state
    app.toggle_panel("menu")
    app.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
    assert app.game.state == before
    app.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert app.panel is None


@pytest.mark.parametrize("key_name,screen_direction", (
    ("K_UP", (-1, -1)), ("K_w", (-1, -1)),
    ("K_DOWN", (1, 1)), ("K_s", (1, 1)),
    ("K_LEFT", (-1, 1)), ("K_a", (-1, 1)),
    ("K_RIGHT", (1, -1)), ("K_d", (1, -1)),
))
@pytest.mark.parametrize("pose", ("standing", "horizontal", "vertical", "split0", "split1"))
def test_keys_follow_visible_board_edges(app, monkeypatch, key_name, screen_direction, pose):
    import pygame
    from BackEnd.logic.board import Board
    from BackEnd.logic.game_rules import GameRules
    from BackEnd.objects.blocks import BlockState, GameState, Orientation
    from BackEnd.objects.tiles import FloorTile

    board = Board()
    for x in range(12):
        for y in range(12):
            board.add_tile(FloorTile(x, y))
    blocks = {
        "standing": BlockState(((4, 4),), Orientation.STANDING),
        "horizontal": BlockState(((4, 4), (5, 4)), Orientation.HORIZONTAL),
        "vertical": BlockState(((4, 4), (4, 5)), Orientation.VERTICAL),
        "split0": BlockState.split(((4, 4), (8, 8)), 0),
        "split1": BlockState.split(((4, 4), (8, 8)), 1),
    }
    before = blocks[pose]
    board.add_game_state(GameState(before))
    app.game.board = board
    app.game.rules = GameRules(board)
    projections = []
    monkeypatch.setattr("FrontEnd.renderer.draw_wood",
                        lambda surface, state, project, scale, animation: projections.append(project))
    app.draw()
    project = projections[0]

    def ground_centre(block):
        positions = (block.positions[block.active_cube],) if block.is_split() else block.positions
        return project(*(sum(p[i] + .5 for p in positions) / len(positions) for i in (0, 1)))

    app.event(pygame.event.Event(pygame.KEYDOWN, key=getattr(pygame, key_name)))
    assert app.game.status == "playing"
    assert len(app.game.history) == 1
    start, end = ground_centre(before), ground_centre(app.game.state.block)
    assert all((end[i] - start[i]) * screen_direction[i] > 0 for i in (0, 1))
    if before.is_split():
        stationary = before.positions[1 - before.active_cube]
        assert stationary in app.game.state.block.positions


def test_fast_keys_keep_one_waiting_turn(app, monkeypatch):
    import pygame
    from BackEnd.objects.sharing import Move

    now = [100.0]
    monkeypatch.setattr("FrontEnd.app.monotonic", lambda: now[0])
    app.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
    now[0] += .1
    app.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT))
    app.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
    assert app.game.state.block.positions == ((5, 6), (6, 6))
    assert app.pending_action == Move.DOWN
    app.process_pending_move()
    assert len(app.game.history) == 1
    now[0] += .2
    app.process_pending_move()
    assert app.game.state.block.positions == ((5, 7), (6, 7))
    assert [action for _, action in app.game.history] == [Move.RIGHT, Move.DOWN]
    assert app.pending_action is None
    now[0] += .3
    app.process_pending_move()
    assert len(app.game.history) == 2


def test_waiting_turn_runs_before_new_key_after_animation(app, monkeypatch):
    import pygame
    from BackEnd.objects.sharing import Move

    now = [100.0]
    monkeypatch.setattr("FrontEnd.app.monotonic", lambda: now[0])
    app.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
    app.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT))
    now[0] += .3
    app.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
    assert [action for _, action in app.game.history] == [Move.RIGHT, Move.DOWN]
    assert app.pending_action == Move.RIGHT


@pytest.mark.parametrize("interrupt", ("menu", "restart", "loss"))
def test_waiting_input_does_not_survive_interrupt(app, interrupt):
    from BackEnd.objects.sharing import Move

    app.animate_move(Move.RIGHT)
    app.animate_move(Move.DOWN)
    assert app.pending_action == Move.DOWN
    if interrupt == "menu":
        app.toggle_panel("menu")
    elif interrupt == "restart":
        app.load_level("map01")
    else:
        app.game.status = "lost"
    before = app.game.state
    app.animation = None
    app.process_pending_move()
    assert app.pending_action is None
    assert app.game.state == before


def test_animation_input_lock_reset_and_terminal_frames(app):
    from BackEnd.objects.sharing import Move
    from time import monotonic
    app.animate_move(Move.RIGHT)
    state = app.game.state
    app.animate_move(Move.DOWN)
    assert app.game.state == state
    for elapsed in (0, .14, .29):
        app.animation['start'] = monotonic() - elapsed
        app.draw()
    app.load_level('map01')
    assert app.animation is None
    for action in 'RDDRRDR':
        app.animation = None
        app.animate_move({'R': Move.RIGHT, 'D': Move.DOWN}[action])
    assert app.game.status == 'won'
    for elapsed in (.14, .4, .7, 1.2):
        app.animation['start'] = monotonic() - elapsed
        app.draw()
    app.load_level('map01')
    invalid = next(move for move in (Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT)
                   if app.game.rules.apply_action(app.game.state, move) is None)
    app.animate_move(invalid)
    assert app.game.status == 'lost'
    for elapsed in (.14, .4, .7, 1.2):
        app.animation['start'] = monotonic() - elapsed
        app.draw()


def test_campaign_unlock_and_victory(app):
    from FrontEnd.progress import Progress
    from BackEnd.objects.sharing import Move
    app.select_stage('map02')
    assert app.game.map_name == 'map01'
    for char in 'RDDRRDR':
        app.animation = None
        app.animate_move({'R': Move.RIGHT, 'D': Move.DOWN}[char])
    app.animation['start'] -= 2
    app.draw()
    assert app.panel == 'win'
    assert app.victory[0] == 7 and app.victory[2] == 3
    restored = Progress(app.progress.path)
    assert restored.unlocked('map02')
    assert not restored.unlocked('map03')
    app.select_stage('map02')
    assert app.game.map_name == 'map02' and app.victory is None


def test_rating_and_best_score(tmp_path):
    from FrontEnd.progress import Progress, stars_for
    assert [stars_for('map01', n) for n in (7, 10, 11)] == [3,2,1]
    progress = Progress(tmp_path / 'save.json')
    progress.complete('map01', 7)
    progress.complete('map01', 15)
    assert Progress(progress.path).records['map01'] == {'moves':7, 'stars':3}
