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
