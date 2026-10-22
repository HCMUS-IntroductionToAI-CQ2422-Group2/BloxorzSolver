"""Uniform-cost search using the shared game rules and search nodes."""

from heapq import heappop, heappush
from itertools import count
from math import inf

from BackEnd.Solver.BaseSolver import BaseSolver
from BackEnd.Solver.SearchNode import SearchNode
from BackEnd.objects.blocks import GameState
from BackEnd.objects.sharing import Move


class UCSSolver(BaseSolver):
    def solve(self, initial_state: GameState) -> list[Move] | None:
        """Return a minimum-cost action sequence, or None if no goal is reachable.

        All game actions cost 1, including SWITCH. Equal-cost entries are
        processed in insertion order, preserving BaseSolver's action order.
        The board and input state are never modified.
        """
        counter = count()
        frontier = [(0, next(counter), SearchNode(state=initial_state))]
        best_cost = {initial_state: 0}

        while frontier:
            _, _, node = heappop(frontier)
            # A cheaper route may have replaced this entry since it was queued.
            if node.path_cost != best_cost[node.state]:
                continue

            # Test on removal, when this state's cheapest path is known.
            if self.rules.is_goal(node.state):
                return self.reconstruct_path(node)

            for action, next_state, step_cost in self.successors(node.state):
                new_cost = node.path_cost + step_cost
                if new_cost >= best_cost.get(next_state, inf):
                    continue

                best_cost[next_state] = new_cost
                child = SearchNode(
                    state=next_state,
                    parent=node,
                    action=action,
                    depth=node.depth + 1,
                    path_cost=new_cost,
                )
                heappush(frontier, (new_cost, next(counter), child))

        return None
