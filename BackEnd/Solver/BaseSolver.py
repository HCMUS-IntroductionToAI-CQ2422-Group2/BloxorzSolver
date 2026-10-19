from abc import ABC, abstractmethod

from BackEnd.logic.game_rules import GameRules
from BackEnd.objects.blocks import GameState
from BackEnd.objects.sharing import Move

from BackEnd.Solver.SearchNode import SearchNode


class BaseSolver(ABC):
    def __init__(self, rules: GameRules):
        self.rules = rules
        for item in self.rules.board.tile:
            if item.type == "Goal": 
                self.x_goal, self.y_goal = item.x, item.y
                break


    def successors(self, state: GameState):
        """Sinh các trạng thái kế tiếp hợp lệ."""
        for action in (
            Move.UP,
            Move.DOWN,
            Move.LEFT,
            Move.RIGHT,
            Move.SWITCH,
        ):
            next_state = self.rules.apply_action(state, action)

            if next_state is not None:
                yield action, next_state, 1

    def reconstruct_path(self, goal_node: SearchNode) -> list[Move]:
        """Truy vết chuỗi hành động từ Initial State đến Goal."""
        actions = []
        node = goal_node

        while node.parent is not None:
            actions.append(node.action)
            node = node.parent

        actions.reverse()
        return actions

    @abstractmethod
    def solve(self, initial_state: GameState):
        """Triển khai thuật toán tìm kiếm."""
        pass