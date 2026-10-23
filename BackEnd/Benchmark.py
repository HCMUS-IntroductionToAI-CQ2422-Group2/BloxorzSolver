"""Common measurement and resource limits for every solver."""

from time import perf_counter
import tracemalloc

from BackEnd.Solver.SearchResult import SearchResult


class SearchLimitReached(Exception):
    """The search stopped before proving whether a solution exists."""


class Benchmark:
    """Measure construction + search, including A* heuristic preparation.

    Run in a dedicated worker process: tracemalloc measures Python allocations,
    not process RSS. Expanded nodes count actual successor generation, excluding
    goal nodes and obsolete priority-queue entries.
    """

    def __init__(self, max_nodes=150_000, time_limit=30.0):
        if max_nodes < 0 or time_limit < 0:
            raise ValueError("Search limits must be non-negative")
        self.max_nodes = max_nodes
        self.time_limit = time_limit
        self.expanded_nodes = 0
        self.started = 0.0

    def check_time(self):
        if perf_counter() - self.started >= self.time_limit:
            raise SearchLimitReached("Time limit reached.")

    def expand(self):
        self.check_time()
        if self.expanded_nodes >= self.max_nodes:
            raise SearchLimitReached("Expanded-node limit reached.")
        self.expanded_nodes += 1

    def run(self, solver_class, rules, initial_state, algorithm):
        self.expanded_nodes = 0
        self.started = perf_counter()
        owns_trace = not tracemalloc.is_tracing()
        if owns_trace:
            tracemalloc.start()
        result = SearchResult(algorithm, "error")
        try:
            self.check_time()
            if not rules.is_valid(initial_state):
                raise ValueError("The initial state is invalid.")
            solver = solver_class(rules, benchmark=self)
            outcome = solver.solve(initial_state)
            self.check_time()
            if isinstance(outcome, SearchResult):
                # DFS keeps main's public result API. The outer measurements
                # below still cover construction and enforce the same limits.
                result = outcome
            else:
                result.status = "solved" if outcome is not None else "no_solution"
                result.actions = outcome if outcome is not None else []
        except SearchLimitReached as error:
            result.status = "limit"
            result.message = str(error)
        except Exception as error:
            result.message = f"{type(error).__name__}: {error}"
        finally:
            result.search_time_s = perf_counter() - self.started
            result.expanded_nodes = self.expanded_nodes
            result.peak_memory_bytes = tracemalloc.get_traced_memory()[1]
            if owns_trace:
                tracemalloc.stop()
        return result
