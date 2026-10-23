from BackEnd.init_map import init_map
from BackEnd.logic.game_rules import GameRules
from BackEnd.objects.sharing import Move


class GameController:
    def __init__(self, map_name="map01"):
        self.load_level(map_name)

    @property
    def state(self):
        return self.board.game_state

    def load_level(self, map_name):
        self.map_name = map_name
        self.board = init_map(map_name)
        self.rules = GameRules(self.board)
        self.status = "playing"
        self.history = []
        self.solution = []
        self.solution_start = None
        self.replay_index = 0
        self.replaying = False
        self.replay_mode = False
        self.result = None

    def restart(self):
        self.load_level(self.map_name)

    def clear_solution(self):
        self.solution = []
        self.solution_start = None
        self.result = None
        self.replay_mode = False
        self.replaying = False
        self.replay_index = 0

    def move(self, action, replay=False):
        if self.status != "playing":
            return False
        if action == Move.SWITCH and not self.state.block.is_split():
            return False
        next_state = self.rules.apply_action(self.state, action)
        if next_state is None:
            self.status = "lost"
            self.replaying = False
            return False
        if not replay:
            self.clear_solution()
        self.history.append((self.state, action))
        self.board.add_game_state(next_state)
        self.status = "won" if self.rules.is_goal(next_state) else "playing"
        return True

    def set_solution(self, result, start):
        self.replaying = False
        self.result = result
        self.solution = result.actions
        self.solution_start = start
        self.replay_mode = False
        self.replay_index = 0

    def start_replay(self):
        if self.solution_start is None or not self.solution:
            return
        self.board.add_game_state(self.solution_start)
        self.history = []
        self.status = "playing"
        self.replay_index = 0
        self.replay_mode = True

    def step(self):
        if not self.solution:
            return
        if not self.replay_mode:
            self.start_replay()
        if self.replay_index < len(self.solution):
            if self.move(self.solution[self.replay_index], replay=True):
                self.replay_index += 1
        if self.replay_index == len(self.solution) or self.status != "playing":
            self.replaying = False
