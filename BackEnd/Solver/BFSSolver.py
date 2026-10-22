"""Breadth-first search over full game states."""

from collections import deque

from BackEnd.Solver.BaseSolver import BaseSolver
from BackEnd.Solver.SearchNode import SearchNode
from BackEnd.objects.blocks import GameState
from BackEnd.objects.sharing import Move


class BFSSolver(BaseSolver):
    def solve(self, initial_state: GameState) -> list[Move] | None:
        frontier = deque([SearchNode(state=initial_state)])
        visited = {initial_state}
        while frontier:
            node = frontier.popleft()
            if self.rules.is_goal(node.state):
                return self.reconstruct_path(node)
            for action, state, cost in self.successors(node.state):
                if state in visited:
                    continue
                visited.add(state)
                frontier.append(SearchNode(
                    state=state, parent=node, action=action,
                    depth=node.depth + 1, path_cost=node.path_cost + cost,
                ))
        return None
