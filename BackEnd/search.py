"""UI entry point: dispatch to the team's solver classes and benchmark them."""

from BackEnd.Benchmark import Benchmark, SearchResult
from BackEnd.Solver.AStarSolver import AStarSolver
from BackEnd.Solver.BFSSolver import BFSSolver
from BackEnd.Solver.DFSSolver import DFSSolver
from BackEnd.Solver.UCSSolver import UCSSolver
from BackEnd.logic.game_rules import GameRules


SOLVERS = {"BFS": BFSSolver, "DFS": DFSSolver, "UCS": UCSSolver, "A*": AStarSolver}


def solve(board, initial_state, algorithm="BFS", max_nodes=150_000, time_limit=30.0):
    try:
        solver_class = SOLVERS[algorithm]
        benchmark = Benchmark(max_nodes=max_nodes, time_limit=time_limit)
        return benchmark.run(solver_class, GameRules(board), initial_state, algorithm)
    except Exception as error:
        return SearchResult(algorithm, "error", message=f"{type(error).__name__}: {error}")


def search_worker(connection, board, initial_state, algorithm, max_nodes, time_limit):
    """Spawn-compatible process target; only this worker owns the measurements."""
    try:
        connection.send(solve(board, initial_state, algorithm, max_nodes, time_limit))
    finally:
        connection.close()
