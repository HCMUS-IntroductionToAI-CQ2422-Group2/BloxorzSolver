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


def test_solver_mode_and_panels_render(app):
    app.toggle_panel("solver")
    app.draw()
    assert app.mode == "solver"
    assert app.panel is None
    app.toggle_panel("menu")
    app.draw()
    app.select_stage("map09")
    assert app.game.map_name == "map09"
    assert app.panel is None
    for name in app.levels:
        app.progress.records[name] = {"stars": 3, "moves": 1}
    for name in app.levels:
        app.load_level(name)
        app.draw()


def wait_for_search(app):
    deadline = time.monotonic() + 15
    while app.worker is not None and time.monotonic() < deadline:
        app.poll_search()
        time.sleep(.01)
    assert app.worker is None, "Search worker did not finish"
    assert app.connection is None
    assert app.game.result is not None
    return app.game.result


@pytest.mark.parametrize("algorithm", ["BFS", "DFS", "UCS", "A*"])
def test_real_worker_benchmark_and_replay(app, algorithm):
    initial = app.game.state
    app.start_search(algorithm)
    assert app.worker is not None
    app.draw()
    result = wait_for_search(app)
    assert result.algorithm == algorithm
    assert result.status == "solved", result.message
    assert result.expanded_nodes > 0
    assert result.search_time_s > 0
    assert result.peak_memory_bytes > 0
    assert app.game.state == initial
    app.draw()
    app.toggle_replay()
    while app.game.replay_index < len(result.actions):
        app.replay_step()
    app.animation = None
    app.draw()
    assert app.game.status == "won"
    assert app.panel is None
    assert app.progress.records == {}
    app.toggle_replay()
    assert app.game.state == initial
    assert app.game.replaying
    app.set_mode("manual")
    assert app.game.status == "playing"
    assert app.game.state == initial
    assert not app.game.replaying


@pytest.mark.parametrize("interrupt", ["escape", "restart", "stage", "manual"])
def test_search_cancellation_discards_old_result(app, interrupt):
    import pygame
    app.start_search("A*")
    if interrupt == "escape":
        app.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    elif interrupt == "restart":
        app.load_level("map01")
    elif interrupt == "stage":
        app.load_level("map09")
    else:
        app.set_mode("manual")
    assert app.worker is None and app.connection is None
    app.poll_search()
    assert app.game.result is None
    assert not app.game.replaying
    app.draw()


def test_second_run_replaces_result_and_manual_move_invalidates_it(app):
    app.start_search("BFS")
    wait_for_search(app)
    app.start_search("UCS")
    assert app.game.result is None
    assert app.game.solution == []
    result = wait_for_search(app)
    assert result.algorithm == "UCS"
    app.animate_move(result.actions[0])
    assert app.game.result is None
    assert not app.game.solution


def test_worker_crash_is_reported(app):
    app.start_search("A*")
    app.worker.terminate()
    app.worker.join(timeout=2)
    app.poll_search()
    assert app.worker is None and app.connection is None
    assert app.game.result.status == "error"
    assert app.game.result.peak_memory_bytes is None


def test_deadline_kills_unresponsive_worker(app, monkeypatch):
    app.start_search("A*")
    monkeypatch.setattr("FrontEnd.app.monotonic", lambda: app.search_began + 33)
    app.poll_search()
    assert app.worker is None
    assert app.game.result.status == "limit"


def test_solver_buttons_start_search_and_replay(app):
    import pygame
    app.set_mode("solver")
    app.draw()
    # Click the actual Run button, then the actual Step button.
    left, top = app.screen.get_width() - 370, 128
    app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(left+30, top+220)))
    assert app.worker is not None
    wait_for_search(app)
    app.draw()
    app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(left+200, top+515)))
    assert app.game.replay_index == 1


def test_export_contains_measured_result_and_search_start(app, tmp_path):
    import csv
    app.start_search("UCS")
    result = wait_for_search(app)
    start = app.game.solution_start
    app.step()
    path = tmp_path / "results" / "benchmark.csv"
    app.export_result(path)
    app.export_result(path)
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 2
    row = rows[0]
    assert row["map"] == "map01"
    assert row["start_state"] == repr(start)
    assert row["algorithm"] == "UCS"
    assert row["status"] == "solved"
    assert int(row["expanded_nodes"]) == result.expanded_nodes
    assert float(row["search_time_s"]) == result.search_time_s
    assert int(row["python_peak_bytes"]) == result.peak_memory_bytes
    assert int(row["solution_length"]) == len(result.actions)
    assert row["actions"] == " ".join(action.value for action in result.actions)


def test_split_cube_switch_replay_does_not_roll_cube(app):
    from BackEnd.objects.sharing import Move
    app.set_mode("solver")
    app.load_level("map09")
    app.start_search("BFS")
    result = wait_for_search(app)
    index = result.actions.index(Move.SWITCH)
    for _ in range(index):
        app.step()
    before = app.game.state.block
    app.step()
    after = app.game.state.block
    assert before.positions == after.positions
    assert before.active_cube != after.active_cube
    assert app.animation is None


def test_worker_limit_shows_no_replay_or_fake_solution(app, monkeypatch):
    monkeypatch.setattr("FrontEnd.app.SEARCH_NODE_LIMIT", 0)
    app.start_search("BFS")
    result = wait_for_search(app)
    assert result.status == "limit"
    assert result.path_cost is None
    app.toggle_replay()
    assert not app.game.replaying
    app.draw()


def test_close_window_disposes_worker(app):
    import pygame
    app.start_search("A*")
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    app.run(frames=1)
    assert app.worker is None and app.connection is None
    assert not app.running


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
