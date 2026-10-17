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
from BackEnd.objects.sharing import Move
from FrontEnd.controller import GameController
from FrontEnd.renderer import ACCENT, BG, MUTED, PANEL, TEXT, Renderer

KEYS = {pygame.K_UP: Move.UP, pygame.K_w: Move.UP,
        pygame.K_DOWN: Move.DOWN, pygame.K_s: Move.DOWN,
        pygame.K_LEFT: Move.LEFT, pygame.K_a: Move.LEFT,
        pygame.K_RIGHT: Move.RIGHT, pygame.K_d: Move.RIGHT,
        pygame.K_SPACE: Move.SWITCH}


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
        self.game = GameController(self.levels[0])
        self.buttons = []
        self.worker = None
        self.connection = None
        self.search_start = None
        self.search_began = 0
        self.algorithm = ""
        self.message = "Roll the block upright into the goal."
        self.speed = 3
        self.last_step = 0
        self.running = True
        self.panel = None
        self.animation = None

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
        if not self.progress.unlocked(name):
            return
        self.stage_started = monotonic()
        self.victory = None
        self.panel = None
        self.animation = None
        self.game.load_level(name)
        self.message = "Arrow keys / WASD to roll. Space to switch cubes."

    def change_level(self, delta):
        index = (self.levels.index(self.game.map_name) + delta) % len(self.levels)
        self.load_level(self.levels[index])

    def start_search(self, algorithm):
        self.choose_solver(algorithm)
        return

    def poll_search(self):
        if self.worker is None:
            return
        if self.connection.poll():
            try:
                result = self.connection.recv()
                self.game.set_solution(result, self.search_start)
                self.message = {"solved": "Solution ready. Press Replay or Step.",
                                "no_solution": "No solution from this position.",
                                "limit": "Search limit reached. Try another algorithm.",
                                "error": result.message}.get(result.status, result.status)
            except (EOFError, OSError):
                self.message = "Search worker stopped without a result."
            self.cancel_search()
        elif not self.worker.is_alive():
            self.message = "Search worker stopped without a result."
            self.cancel_search()

    def toggle_replay(self):
        if not self.game.solution:
            return
        if self.game.replaying:
            self.game.replaying = False
            return
        if not self.game.replay_mode or self.game.replay_index == len(self.game.solution):
            self.game.start_replay()
        self.game.replaying = True
        self.last_step = monotonic()

    def step(self):
        self.game.replaying = False
        self.game.step()

    def export_result(self):
        result = self.game.result
        if result is None:
            return
        path = Path(__file__).resolve().parents[1] / "output" / "search_results.csv"
        try:
            path.parent.mkdir(exist_ok=True)
            exists = path.exists() and path.stat().st_size > 0
            with path.open("a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                if not exists:
                    writer.writerow(["map", "start_state", "algorithm", "status", "search_time_s",
                                     "python_peak_bytes", "expanded_nodes", "solution_length", "actions"])
                writer.writerow([self.game.map_name, repr(self.game.solution_start), result.algorithm,
                                 result.status, result.search_time_s, result.peak_memory_bytes,
                                 result.expanded_nodes, len(result.actions),
                                 " ".join(action.value for action in result.actions)])
            self.message = "Saved to output/search_results.csv"
        except OSError as error:
            self.message = f"Export failed: {error}"

    def button(self, label, rect, callback, enabled=True, selected=False):
        rect = pygame.Rect(rect)
        hover = rect.collidepoint(pygame.mouse.get_pos()) and enabled
        color = ACCENT if selected else ("#64463b" if hover else "#412d29")
        if not enabled:
            color = "#2f2424"
        pygame.draw.rect(self.screen, color, rect, border_radius=7)
        text_color = BG if selected else (TEXT if enabled else "#586d88")
        text = self.renderer.fonts[16].render(label, True, text_color)
        self.screen.blit(text, text.get_rect(center=rect.center))
        self.buttons.append((rect, callback, enabled))

    def toggle_panel(self, name):
        self.panel = None if self.panel == name else name

    def select_stage(self, name):
        self.load_level(name)
        self.panel = None

    def choose_solver(self, name):
        self.algorithm = name

    def draw(self):
        self.check_victory()
        self.buttons = []
        surface, r, game = self.screen, self.renderer, self.game
        width, height = surface.get_size()
        r.background(surface)
        r.text(surface, "BLOXORZ", (36, 25), 32)

        self.button("Menu", (width - 260, 28, 110, 44), lambda: self.toggle_panel("menu"))
        self.button("", (width - 130, 28, 90, 44), lambda: self.toggle_panel("solver"))
        cx = width - 85
        pygame.draw.circle(surface, "#f8d687", (cx, 45), 9, 2)
        pygame.draw.line(surface, "#f8d687", (cx-5, 55), (cx+5, 55), 3)
        pygame.draw.line(surface, "#f8d687", (cx-3, 60), (cx+3, 60), 2)
        r.text(surface, self.maps[game.map_name]["name"] + "  /  " + str(len(game.history)) + " moves", (38, 113), 18)
        r.board(surface, game.board, game.state, pygame.Rect(50, 160, width-100, height-300), self.animation)
        status = {"playing": "", "won": "STAGE COMPLETE!", "lost": "You fell. Press R to restart."}[game.status]
        r.text(surface, status, (38, height-107), 22, ACCENT)
        r.text(surface, "Arrows / WASD: move   |   Space: switch cube   |   R: restart   |   Esc: close menu", (38, height-69), 16, MUTED)

        if self.panel:
            self.buttons = []
            shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            shade.fill((3, 12, 19, 185))
            surface.blit(shade, (0, 0))
            box = pygame.Rect(width//2-270, height//2-250, 540, 500)
            pygame.draw.rect(surface, PANEL, box, border_radius=24)
            pygame.draw.rect(surface, "#526d75", box, 1, border_radius=24)
            x, y = box.x+32, box.y+30
            self.button("X", (box.right-70, y, 40, 36), lambda: self.toggle_panel(self.panel))
            if self.panel == "win":
                self.draw_victory(x, y)
            elif self.panel == "menu":
                r.text(surface, "Your next adventure", (x, y), 22)
                r.text(surface, "Choose a stage", (x, y+45), 16, MUTED)
                for index, level in enumerate(self.levels):
                    row, col = divmod(index, 5)
                    self.button(str(index+1).zfill(2) if self.progress.unlocked(level) else "Locked", (x+col*96, y+85+row*57, 86, 46), lambda name=level: self.select_stage(name), selected=level == game.map_name, enabled=self.progress.unlocked(level))
                self.button("Restart stage", (x, y+330, 220, 44), lambda: self.select_stage(game.map_name))
                self.button("Resume", (x+238, y+330, 236, 44), lambda: self.toggle_panel("menu"))
                r.text(surface, "O Soft   X Heavy   ( ) Split   Orange: fragile", (x, y+404), 16, MUTED)
            else:
                r.text(surface, "Need a little light?", (x, y), 22)
                r.text(surface, "Choose a search algorithm", (x, y+48), 16, MUTED)
                for index, name in enumerate(("BFS", "DFS", "UCS", "A*")):
                    self.button(name, (x, y+91+index*62, 474, 48), lambda algo=name: self.choose_solver(algo), selected=self.algorithm == name)


        pygame.display.flip()

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
            elif self.panel:
                return
            elif event.key == pygame.K_r:
                self.load_level(self.game.map_name)
            elif event.key == pygame.K_ESCAPE:
                self.cancel_search()
                self.game.replaying = False
            elif event.key in KEYS and self.worker is None and not self.game.replaying:
                self.animate_move(KEYS[event.key])

    def animate_move(self, action):
        if self.animation and monotonic() - self.animation["start"] < self.animation["duration"]:
            return
        if self.game.status != "playing":
            return
        before = self.game.state
        if action == Move.SWITCH:
            self.game.move(action)
            return
        self.game.move(action)
        if self.game.status == "won":
            self.finished_seconds = monotonic() - self.stage_started
        self.animation = {"before": before, "after": self.game.state,
                          "action": action, "status": self.game.status,
                          "start": monotonic(),
                          "duration": .28 if self.game.status == "playing" else 1.1}

    def check_victory(self):
        if self.game.status != "won" or self.victory is not None:
            return
        if self.animation and monotonic() - self.animation["start"] < 1.1:
            return
        moves = len(self.game.history)
        stars = stars_for(self.game.map_name, moves)
        try:
            self.progress.complete(self.game.map_name, moves)
            saved = True
        except OSError:
            saved = False
        self.victory = (moves, getattr(self, "finished_seconds", 0), stars, saved)
        self.panel = "win"

    def draw_victory(self, x, y):
        r, surface = self.renderer, self.screen
        moves, seconds, stars, saved = self.victory
        r.text(surface, "Stage complete", (x, y), 32)
        for index in range(3):
            cx, cy = x+110+index*125, y+115
            points = [(cx+math.cos(-math.pi/2+i*math.pi/5)*(37 if i%2==0 else 17),
                       cy+math.sin(-math.pi/2+i*math.pi/5)*(37 if i%2==0 else 17)) for i in range(10)]
            pygame.draw.polygon(surface, "#efbc65" if index<stars else "#514543", points)
        r.text(surface, f"Moves: {moves}       Time: {int(seconds)//60:02}:{int(seconds)%60:02}", (x+65, y+188), 22)
        target = TARGETS[self.game.map_name]
        r.text(surface, f"3 stars: {target} moves   /   2 stars: {int(target*1.5)} moves", (x+48, y+237), 16, MUTED)
        self.button("Play again", (x,y+304,224,48), lambda: self.select_stage(self.game.map_name))
        index = self.levels.index(self.game.map_name)
        if index+1 < len(self.levels):
            self.button("Next stage", (x+240,y+304,234,48), lambda: self.select_stage(self.levels[index+1]))
        else:
            self.button("All stages complete", (x+240,y+304,234,48), lambda: self.toggle_panel("menu"))
        if not saved:
            r.text(surface, "Progress could not be saved.", (x,y+386), 16, MUTED)

    def run(self, frames=None, screenshot=None):
        frame = 0
        try:
            self.draw()
            while self.running:
                for event in pygame.event.get():
                    self.event(event)
                self.poll_search()
                if self.game.replaying and monotonic() - self.last_step >= 1 / self.speed:
                    self.game.step()
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
