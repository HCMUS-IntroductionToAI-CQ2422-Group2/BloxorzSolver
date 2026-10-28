"""Responsive desktop GUI with cancellable process-isolated search."""
import argparse
import math
from FrontEnd.progress import Progress, TARGETS, stars_for
import csv
import json
import multiprocessing
from pathlib import Path
from time import monotonic

import pygame

from BackEnd.init_map import MAPS_PATH
from BackEnd.Benchmark import SearchResult
from BackEnd.objects.sharing import Move
from BackEnd.search import SOLVERS, search_worker
from FrontEnd.controller import GameController
from FrontEnd.fall_motion import prepare_fall
from FrontEnd.renderer import ACCENT, BG, MUTED, PANEL, TEXT, Renderer

# Match the four visible edges of the isometric board: NW, SE, SW, NE.
KEYS = {pygame.K_UP: Move.LEFT, pygame.K_w: Move.LEFT,
        pygame.K_DOWN: Move.RIGHT, pygame.K_s: Move.RIGHT,
        pygame.K_LEFT: Move.DOWN, pygame.K_a: Move.DOWN,
        pygame.K_RIGHT: Move.UP, pygame.K_d: Move.UP,
        pygame.K_SPACE: Move.SWITCH}

LOSS_ANIMATION_SECONDS = 1.1
SEARCH_TIME_LIMIT = 30.0
SEARCH_NODE_LIMIT = 150_000


def _ease_out_back(t):
    """Overshoot easing (0..1 -> slightly past 1 then settle) used for the star pop-in."""
    t = max(0.0, min(1.0, t))
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


class App:
    def __init__(self, progress_path=None):
        pygame.init()
        pygame.display.set_caption("Bloxorz | Search Lab")
        self.screen = pygame.display.set_mode((1180, 800), pygame.RESIZABLE)
        self.renderer = Renderer()
        self.clock = pygame.time.Clock()
        with MAPS_PATH.open(encoding="utf-8") as file:
            self.maps = json.load(file)
        self.levels = list(self.maps)
        self.progress = Progress(progress_path)
        self.stage_started = monotonic()
        self.victory = None
        self.victory_shown = 0
        self.game = GameController(self.levels[0])
        self.buttons = []
        self.worker = None
        self.connection = None
        self.search_start = None
        self.search_began = 0
        self.algorithm = "BFS"
        self.mode = "manual"
        self.message = "Roll the block upright into the goal."
        self.speed = 3
        self.last_step = 0
        self.running = True
        self.panel = None
        self.animation = None
        self.pending_action = None

    def cancel_search(self):
        if self.worker is not None:
            if self.worker.is_alive():
                self.worker.terminate()
            self.worker.join(timeout=1)
            self.worker.close()
            self.worker = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def load_level(self, name):
        self.cancel_search()
        if self.mode == "manual" and not self.progress.unlocked(name):
            return
        self.stage_started = monotonic()
        self.victory = None
        self.panel = None
        self.animation = None
        self.pending_action = None
        self.game.load_level(name)
        self.message = "Arrow keys / WASD to roll. Space to switch cubes."

    def set_mode(self, mode):
        if mode == self.mode:
            self.panel = None
            return
        self.cancel_search()
        self.game.replaying = False
        self.pending_action = None
        self.panel = None
        self.mode = mode
        if mode == "manual":
            # Solver replays must not unlock stages or award campaign stars.
            name = self.game.map_name
            self.load_level(name if self.progress.unlocked(name) else self.levels[0])
        else:
            self.victory = None
            self.message = "Choose an algorithm, then run from the current position."

    def change_level(self, delta):
        index = (self.levels.index(self.game.map_name) + delta) % len(self.levels)
        self.load_level(self.levels[index])

    def start_search(self, algorithm=None):
        if self.game.status == "lost":
            return
        self.set_mode("solver")
        if algorithm is not None:
            self.choose_solver(algorithm)
        self.cancel_search()
        self.game.replaying = False
        # Restart the stage so every algorithm is compared from the same
        # starting position instead of wherever a previous replay left it.
        self.game.load_level(self.game.map_name)
        self.animation = None
        self.pending_action = None
        self.victory = None
        self.search_start = self.game.state
        self.search_began = monotonic()
        context = multiprocessing.get_context("spawn")
        self.connection, sender = context.Pipe(duplex=False)
        worker = context.Process(
            target=search_worker,
            args=(sender, self.game.board, self.search_start, self.algorithm,
                  SEARCH_NODE_LIMIT, SEARCH_TIME_LIMIT),
            daemon=True,
        )
        try:
            worker.start()
            self.worker = worker
            self.message = f"Running {self.algorithm}..."
        except Exception as error:
            worker.close()
            self.connection.close()
            self.connection = None
            self.record_search_error(f"Could not start search: {error}")
        finally:
            sender.close()

    def record_search_error(self, message, status="error"):
        result = SearchResult(
            self.algorithm, status, message=message,
            search_time_s=monotonic() - self.search_began,
            expanded_nodes=None, peak_memory_bytes=None,
        )
        self.game.set_solution(result, self.search_start)
        self.message = message

    def stop_search(self):
        self.cancel_search()
        self.message = "Search cancelled. Choose an algorithm to run again."

    def poll_search(self):
        if self.worker is None:
            return
        if self.connection.poll():
            try:
                result = self.connection.recv()
                self.game.set_solution(result, self.search_start)
                self.message = {"solved": ("Already at the goal." if not result.actions else
                                          "Solution ready. Press Replay or Step."),
                                "no_solution": "No solution from this position.",
                                "limit": result.message + " Try another algorithm.",
                                "error": result.message}.get(result.status, result.status)
            except (EOFError, OSError):
                self.record_search_error("Search worker stopped without a result.")
            self.cancel_search()
        elif not self.worker.is_alive():
            self.record_search_error("Search worker stopped without a result.")
            self.cancel_search()
        elif monotonic() - self.search_began > SEARCH_TIME_LIMIT + 2:
            self.record_search_error("Worker time limit reached.", status="limit")
            self.cancel_search()

    def toggle_replay(self):
        if self.worker is not None or not self.game.solution:
            return
        if self.game.replaying:
            self.game.replaying = False
            return
        if not self.game.replay_mode or self.game.replay_index == len(self.game.solution):
            self.game.start_replay()
        self.game.replaying = True
        self.panel = None
        self.animation = None
        self.victory = None
        self.last_step = monotonic()

    def step(self):
        if self.worker is not None:
            return
        self.game.replaying = False
        self.replay_step()

    def replay_step(self):
        if not self.game.solution:
            return
        if not self.game.replay_mode:
            self.game.start_replay()
        before = self.game.state
        index = self.game.replay_index
        self.game.step()
        if self.game.replay_index > index:
            if self.game.solution[index] == Move.SWITCH:
                self.animation = None
                return
            self.animation = {"before": before, "after": self.game.state,
                              "action": self.game.solution[index],
                              "status": self.game.status, "start": monotonic(),
                              "duration": min(.28, 1 / self.speed)}

    def export_result(self, path=None):
        result = self.game.result
        if result is None:
            return
        path = Path(path) if path else Path(__file__).resolve().parents[1] / "output" / "search_results.csv"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            exists = path.exists() and path.stat().st_size > 0
            with path.open("a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                if not exists:
                    writer.writerow(["map", "start_state", "algorithm", "status", "search_time_s",
                                     "python_peak_bytes", "expanded_nodes", "solution_length", "actions"])
                writer.writerow([self.game.map_name, repr(self.game.solution_start), result.algorithm,
                                 result.status, result.search_time_s, result.peak_memory_bytes,
                                 result.expanded_nodes, result.path_cost,
                                 " ".join(action.value for action in result.actions)])
            self.message = "Saved to output/search_results.csv"
        except OSError as error:
            self.message = f"Export failed: {error}"

    def button(self, label, rect, callback, enabled=True, selected=False, emphasized=False):
        rect = pygame.Rect(rect)
        hover = rect.collidepoint(pygame.mouse.get_pos()) and enabled
        color = ACCENT if selected else ("#64463b" if hover else "#412d29")
        if not enabled:
            color = "#2f2424"
        if emphasized:
            pygame.draw.rect(self.screen, "#1a1210", rect.move(0, 4), border_radius=9)
        pygame.draw.rect(self.screen, color, rect, border_radius=7)
        if emphasized:
            pygame.draw.rect(self.screen, ACCENT, rect, 2, border_radius=7)
        text_color = BG if selected else (TEXT if enabled else "#586d88")
        text = self.renderer.fonts[16].render(label, True, text_color)
        self.screen.blit(text, text.get_rect(center=rect.center))
        self.buttons.append((rect, callback, enabled))

    def toggle_panel(self, name):
        self.pending_action = None
        self.game.replaying = False
        if name == "solver":
            self.set_mode("solver")
            return
        self.panel = None if self.panel == name else name

    def select_stage(self, name):
        self.load_level(name)
        self.panel = None

    def choose_solver(self, name):
        if name not in SOLVERS:
            raise ValueError(f"Unknown algorithm: {name}")
        self.algorithm = name

    def draw(self):
        self.check_victory()
        self.check_defeat()
        self.buttons = []
        surface, r, game = self.screen, self.renderer, self.game
        width, height = surface.get_size()
        r.background(surface)
        r.text(surface, "BLOXORZ", (36, 25), 32)

        self.button("Play manually", (width-630, 28, 150, 44),
                    lambda: self.set_mode("manual"), selected=self.mode == "manual")
        self.button("Solve by algorithm", (width-468, 28, 190, 44),
                    lambda: self.set_mode("solver"), selected=self.mode == "solver")
        self.button("Stages", (width-266, 28, 104, 44), lambda: self.toggle_panel("menu"))
        self.button("Restart", (width-150, 28, 110, 44), lambda: self.load_level(game.map_name))
        r.text(surface, self.maps[game.map_name]["name"] + "  /  " + str(len(game.history)) + " moves", (38, 113), 18)
        board_width = width - (470 if self.mode == "solver" else 100)
        r.board(surface, game.board, game.state, pygame.Rect(50, 160, board_width, height-300), self.animation)
        status = {"playing": "", "won": "STAGE COMPLETE!", "lost": "You fell! Restarting..."}[game.status]
        r.text(surface, status, (38, height-107), 22, ACCENT)
        r.text(surface, "Up/W: upper-left   Right/D: upper-right   Down/S: lower-right   Left/A: lower-left", (38, height-79), 16, MUTED)
        r.text(surface, "Space: switch cube   |   R: restart   |   Esc: cancel / pause / close", (38, height-55), 16, MUTED)

        if self.mode == "solver":
            self.draw_solver(pygame.Rect(width-390, 108, 350, height-142))

        if self.panel:
            self.buttons = []
            shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            shade.fill((3, 12, 19, 185))
            surface.blit(shade, (0, 0))

            box_height = 500
            cols, rows, row_pitch, grid_top, button_h, footer_gap, footer_h, caption_gap = (5, 1, 57, 85, 46, 20, 44, 20)
            if self.panel == "menu":
                # The stage grid grows with the level count (35 now, more
                # later), so the panel height and the footer/caption below
                # it must follow instead of a size tuned for ~20 levels.
                cols = 5
                rows = -(-len(self.levels) // cols)
                caption_h = 20
                bottom_pad = 30
                content_height = (grid_top + (rows - 1) * row_pitch + button_h
                                   + footer_gap + footer_h + caption_gap + caption_h + bottom_pad)
                max_box_height = height - 80
                if content_height > max_box_height and rows > 1:
                    available = max_box_height - (grid_top + button_h + footer_gap
                                                    + footer_h + caption_gap + caption_h + bottom_pad)
                    row_pitch = max(40, available / (rows - 1))
                    content_height = max_box_height
                box_height = min(content_height, max_box_height)

            box = pygame.Rect(width//2-270, height//2-box_height//2, 540, box_height)
            pygame.draw.rect(surface, PANEL, box, border_radius=24)
            border_color = ACCENT if self.panel == "win" else "#526d75"
            border_width = 3 if self.panel == "win" else 1
            pygame.draw.rect(surface, border_color, box, border_width, border_radius=24)
            x, y = box.x+32, box.y+30
            self.button("X", (box.right-70, y, 40, 36), lambda: self.toggle_panel(self.panel))
            if self.panel == "win":
                self.draw_victory(x, y)
            elif self.panel == "menu":
                r.text(surface, "Your next adventure", (x, y), 22)
                r.text(surface, "Choose a stage", (x, y+45), 16, MUTED)
                for index, level in enumerate(self.levels):
                    row, col = divmod(index, cols)
                    unlocked = self.mode == "solver" or self.progress.unlocked(level)
                    self.button(str(index+1).zfill(2) if unlocked else "Locked", (x+col*96, y+grid_top+row*row_pitch, 86, 46), lambda name=level: self.select_stage(name), selected=level == game.map_name, enabled=unlocked)
                footer_y = y + grid_top + (rows - 1) * row_pitch + button_h + footer_gap
                self.button("Restart stage", (x, footer_y, 220, 44), lambda: self.select_stage(game.map_name))
                self.button("Resume", (x+238, footer_y, 236, 44), lambda: self.toggle_panel("menu"))
                r.text(surface, "O Soft   X Heavy   •• Split   Orange: fragile", (x, footer_y + footer_h + caption_gap), 16, MUTED)


        pygame.display.flip()

    def wrapped_text(self, value, x, y, width, max_lines=2, color=MUTED):
        font = self.renderer.fonts[14]
        words = value.split()
        lines = []
        line = ""
        for word in words:
            candidate = (line + " " + word).strip()
            if line and font.size(candidate)[0] > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        for index, line in enumerate(lines[:max_lines]):
            if index == max_lines-1 and len(lines) > max_lines:
                line = line.rstrip(".") + "..."
            if font.size(line)[0] > width:
                while line and font.size(line + "...")[0] > width:
                    line = line[:-1]
                line += "..."
            self.renderer.text(self.screen, line, (x, y+index*19), 14, color)

    def draw_solver(self, box):
        surface, r, game = self.screen, self.renderer, self.game
        pygame.draw.rect(surface, PANEL, box, border_radius=18)
        pygame.draw.rect(surface, "#705448", box, 1, border_radius=18)
        x, y = box.x+20, box.y+20
        busy = self.worker is not None
        r.text(surface, "Solve by algorithm", (x, y), 22)
        r.text(surface, "Starts from the current board position", (x, y+31), 14, MUTED)
        for index, name in enumerate(SOLVERS):
            row, col = divmod(index, 2)
            self.button(name, (x+col*160, y+62+row*46, 150, 38),
                        lambda algo=name: self.choose_solver(algo),
                        enabled=not busy, selected=self.algorithm == name)
        descriptions = {
            "BFS": "Breadth-first search. Fewest moves with unit costs.",
            "DFS": "Depth-first search. Finds a path; may use more moves.",
            "UCS": "Lowest cost first. Every move and cube switch costs 1.",
            "A*": "Cost + heuristic. Includes heuristic preparation in timing.",
        }
        self.wrapped_text(descriptions[self.algorithm], x, y+155, 310)
        self.button("Cancel search" if busy else f"Run {self.algorithm}",
                    (x, y+202, 310, 42), self.stop_search if busy else self.start_search,
                    enabled=busy or game.status != "lost", emphasized=True)
        r.text(surface, "Limit: 30 seconds / 150,000 expanded nodes", (x, y+252), 14, MUTED)
        message = (f"Running {self.algorithm}... {monotonic()-self.search_began:.1f}s"
                   if busy else self.message)
        self.wrapped_text(message, x, y+278, 310, max_lines=2, color=TEXT)
        result = game.result
        title = f"Benchmark - {result.algorithm}" if result else "Benchmark"
        r.text(surface, title, (x, y+328), 18, ACCENT)
        if result:
            time_text = f"{result.search_time_s:.4f} s"
            memory = (f"{result.peak_memory_bytes / 1048576:.3f} MiB"
                      if result.peak_memory_bytes is not None else "Unavailable")
            nodes = f"{result.expanded_nodes:,}" if result.expanded_nodes is not None else "Unavailable"
            moves = str(result.path_cost) if result.path_cost is not None else "--"
        else:
            time_text = memory = nodes = moves = "--"
        for index, (label, value) in enumerate((
            ("Elapsed time", time_text), ("Python peak memory", memory),
            ("Expanded nodes", nodes), ("Solution moves / cost", moves),
        )):
            row, col = divmod(index, 2)
            left, top = x+col*160, y+360+row*54
            r.text(surface, label, (left, top), 14, MUTED)
            r.text(surface, value, (left, top+19), 18)
        r.text(surface, "Memory is Python allocations, not process RAM.", (x, y+469), 14, MUTED)
        can_replay = not busy and result is not None and result.status == "solved" and bool(game.solution)
        self.button("Pause" if game.replaying else "Replay", (x, y+498, 150, 38),
                    self.toggle_replay, enabled=can_replay)
        self.button("Step", (x+160, y+498, 150, 38), self.step,
                    enabled=can_replay and game.replay_index < len(game.solution))
        self.button("-", (x, y+546, 36, 34), lambda: self.set_speed(-1), enabled=self.speed > 1)
        r.text(surface, f"{self.speed} moves/s", (x+45, y+553), 14)
        self.button("+", (x+130, y+546, 36, 34), lambda: self.set_speed(1), enabled=self.speed < 10)
        self.button("Export CSV", (x+176, y+546, 134, 34), self.export_result,
                    enabled=result is not None and not busy)
        r.text(surface, f"Replay: {game.replay_index} / {len(game.solution)} moves", (x, y+599), 14, MUTED)

    def set_speed(self, delta):
        self.speed = max(1, min(10, self.speed + delta))

    def event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.set_mode((max(1060, event.w), max(800, event.h)), pygame.RESIZABLE)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, callback, enabled in self.buttons:
                if enabled and rect.collidepoint(event.pos):
                    callback()
                    break
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.panel = None
                self.game.replaying = False
                self.pending_action = None
                if self.worker is not None:
                    self.stop_search()
            elif self.panel:
                return
            elif event.key == pygame.K_r:
                self.load_level(self.game.map_name)
            elif event.key in KEYS and self.worker is None and not self.game.replaying:
                self.process_pending_move()
                self.animate_move(KEYS[event.key])

    def animate_move(self, action):
        if self.game.status != "playing":
            return
        if self.animation and monotonic() - self.animation["start"] < self.animation["duration"]:
            if self.pending_action is None:
                self.pending_action = action
            return
        self.pending_action = None
        before = self.game.state
        if action == Move.SWITCH:
            if self.game.move(action) and self.mode == "solver":
                self.message = "Position changed. Running a search restarts the stage."
            return
        self.game.move(action)
        if self.mode == "solver":
            self.message = "Position changed. Running a search restarts the stage."
        if self.game.status == "won":
            self.finished_seconds = monotonic() - self.stage_started
        self.animation = {"before": before, "after": self.game.state,
                          "action": action, "status": self.game.status,
                          "start": monotonic(),
                          "duration": .28 if self.game.status == "playing" else LOSS_ANIMATION_SECONDS}

        if self.game.status == "lost":
            self.animation["fall_plan"] = prepare_fall(self.game.rules, before, action)

    def process_pending_move(self):
        if self.pending_action is None:
            return
        if self.panel or self.worker is not None or self.game.replaying or self.game.status != "playing":
            self.pending_action = None
            return
        if self.animation and monotonic() - self.animation["start"] < self.animation["duration"]:
            return
        action = self.pending_action
        self.pending_action = None
        self.animate_move(action)

    def check_victory(self):
        if self.mode == "solver" or self.game.replay_mode:
            return
        if self.game.status != "won" or self.victory is not None:
            return
        if self.animation and monotonic() - self.animation["start"] < LOSS_ANIMATION_SECONDS:
            return
        moves = len(self.game.history)
        stars = stars_for(self.game.map_name, moves)
        try:
            self.progress.complete(self.game.map_name, moves)
            saved = True
        except OSError:
            saved = False
        self.victory = (moves, getattr(self, "finished_seconds", 0), stars, saved)
        self.victory_shown = monotonic()
        self.panel = "win"

    def check_defeat(self):
        """After a fall finishes playing out, restart the stage without requiring R."""
        if self.game.status != "lost":
            return
        if (self.animation and self.animation.get("status") == "lost"
                and monotonic() - self.animation["start"] < LOSS_ANIMATION_SECONDS):
            return
        self.load_level(self.game.map_name)

    def draw_victory(self, x, y):
        r, surface = self.renderer, self.screen
        moves, seconds, stars, saved = self.victory
        elapsed = monotonic() - self.victory_shown
        r.text(surface, "Stage complete", (x, y), 32)
        r.text(surface, "Nice rolling!", (x, y+34), 16, MUTED)

        star_center_y = y+150
        glow = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        glow_x, glow_y = x+237, star_center_y
        for radius in range(100, 20, -4):
            pygame.draw.circle(glow, (255, 196, 110, 5), (glow_x, glow_y), radius)
        surface.blit(glow, (0, 0))
        for index in range(3):
            local_t = (elapsed - index*.12) / .3
            pop = 0 if local_t <= 0 else _ease_out_back(min(1, local_t))
            cx, cy = x+120+index*117, star_center_y
            points = [(cx+math.cos(-math.pi/2+i*math.pi/5)*(37 if i%2==0 else 17)*pop,
                       cy+math.sin(-math.pi/2+i*math.pi/5)*(37 if i%2==0 else 17)*pop) for i in range(10)]
            pygame.draw.polygon(surface, "#efbc65" if index<stars else "#514543", points)

        r.text(surface, f"Moves: {moves}       Time: {int(seconds)//60:02}:{int(seconds)%60:02}", (x+58, y+230), 22)
        target = TARGETS[self.game.map_name]
        r.text(surface, f"3 stars: {target} moves   /   2 stars: {int(target*1.5)} moves", (x+40, y+268), 16, MUTED)
        pygame.draw.line(surface, "#4a3a32", (x, y+312), (x+474, y+312), 1)

        self.button("Play again", (x, y+340, 224, 52), lambda: self.select_stage(self.game.map_name), emphasized=True)
        index = self.levels.index(self.game.map_name)
        if index+1 < len(self.levels):
            self.button("Next stage", (x+240, y+340, 234, 52), lambda: self.select_stage(self.levels[index+1]), emphasized=True)
        else:
            self.button("All stages complete", (x+240, y+340, 234, 52), lambda: self.toggle_panel("menu"))
        if not saved:
            r.text(surface, "Progress could not be saved.", (x, y+412), 16, MUTED)

    def run(self, frames=None, screenshot=None):
        frame = 0
        try:
            self.draw()
            while self.running:
                for event in pygame.event.get():
                    self.event(event)
                self.poll_search()
                self.process_pending_move()
                if self.game.replaying and not self.panel and monotonic() - self.last_step >= 1 / self.speed:
                    self.replay_step()
                    self.last_step = monotonic()
                self.draw()
                self.clock.tick(60)
                frame += 1
                if frames is not None and frame >= frames:
                    if screenshot:
                        Path(screenshot).parent.mkdir(parents=True, exist_ok=True)
                        pygame.image.save(self.screen, screenshot)
                    break
        finally:
            self.cancel_search()
            pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Bloxorz desktop GUI")
    parser.add_argument("--frames", type=int, help="Exit after N frames (smoke testing)")
    parser.add_argument("--screenshot", help="Save the last frame when using --frames")
    args = parser.parse_args()
    App().run(args.frames, args.screenshot)
