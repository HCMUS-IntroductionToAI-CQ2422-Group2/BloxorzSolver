"""Depth-first graph search; finds a valid path, not necessarily a shortest one."""

from BackEnd.Solver.BaseSolver import BaseSolver
from BackEnd.Solver.SearchNode import SearchNode
from BackEnd.objects.blocks import GameState
from BackEnd.objects.sharing import Move


class DFSSolver(BaseSolver):
    def solve(self, initial_state: GameState) -> list[Move] | None:
        frontier = [SearchNode(state=initial_state)]
        visited = {initial_state}
        while frontier:
            node = frontier.pop()
            if self.rules.is_goal(node.state):
                return self.reconstruct_path(node)
            # Reverse the push order so UP is explored first with a LIFO stack.
            for action, state, cost in reversed(list(self.successors(node.state))):
                if state in visited:
                    continue
                visited.add(state)
                frontier.append(SearchNode(
                    state=state, parent=node, action=action,
                    depth=node.depth + 1, path_cost=node.path_cost + cost,
                ))
        return None
