from time import perf_counter
import tracemalloc

from BackEnd.Benchmark import SearchLimitReached

from BackEnd.Solver.BaseSolver import BaseSolver
from BackEnd.Solver.SearchNode import SearchNode
from BackEnd.Solver.SearchResult import SearchResult
from BackEnd.objects.blocks import GameState


class DFSSolver(BaseSolver):
    def solve(self, initial_state: GameState) -> SearchResult:
        result = SearchResult(algorithm="DFS", status="no_solution")
        started_at = perf_counter()
        owns_tracing = not tracemalloc.is_tracing()
        if owns_tracing:
            tracemalloc.start()

        try:
            if not self.rules.is_valid(initial_state):
                result.status = "error"
                result.message = "Trạng thái đầu vào không hợp lệ."
                return result

            root = SearchNode(state=initial_state)
            stack = [root]
            visited: set[GameState] = set()

            while stack:
                node = stack.pop()
                if node.state in visited:
                    continue
                visited.add(node.state)

                if self.rules.is_goal(node.state):
                    result.status = "solved"
                    result.actions = self.reconstruct_path(node)
                    return result

                result.expanded_nodes += 1
                children = list(self.successors(node.state))

                for action, next_state, cost in reversed(children):
                    if next_state in visited:
                        continue
                    child = SearchNode(
                        state=next_state,
                        parent=node,
                        action=action,
                        depth=node.depth + 1,
                        path_cost=node.path_cost + cost,
                    )
                    stack.append(child)

            result.message = "Không có lời giải từ trạng thái đầu vào."
            return result
        except SearchLimitReached:
            raise
        except Exception as error:
            result.status = "error"
            result.message = f"{type(error).__name__}: {error}"
            return result
        finally:
            result.search_time_s = perf_counter() - started_at
            if owns_tracing:
                result.peak_memory_bytes = tracemalloc.get_traced_memory()[1]
                tracemalloc.stop()
