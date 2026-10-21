from BackEnd.Solver.BaseSolver import BaseSolver
from BackEnd.objects.sharing import Move
from BackEnd.Solver.SearchNode import SearchNode
from BackEnd.logic.game_rules import GameRules
from BackEnd.objects.blocks import BlockState, GameState, Orientation
from BackEnd.logic.board import Board
from BackEnd.objects.switchs import Switch
from BackEnd.objects.tiles import Goal
from collections import defaultdict, deque
from dataclasses import replace
from itertools import combinations
import math
from queue import PriorityQueue

class AStarSolver(BaseSolver): 
    def __init__(self, rules):
        super().__init__(rules)
        self.heuristic_table = self._build_heuristic_table()
        
    def _heuristic_function(self, state: GameState):
        return self.heuristic_table.get(state.block, math.inf)

    def _build_heuristic_table(self):
        relaxed_board = Board()
        for tile in self.rules.board.tile:
            relaxed_board.add_tile(replace(tile, effects=()) if isinstance(tile, Switch) else tile)
        for bridge in self.rules.board.bridge:
            relaxed_board.add_bridge(bridge)

        rules = GameRules(relaxed_board)
        open_bridges = frozenset(bridge.bridge_id for bridge in relaxed_board.bridge)
        positions = sorted({
            position
            for tile in [*relaxed_board.tile, *relaxed_board.bridge]
            for position in tile.get_positions()
        })
        position_set = set(positions)
        blocks = []
        for x, y in positions:
            blocks.append(BlockState(((x, y),), Orientation.STANDING))
            if (x + 1, y) in position_set:
                blocks.append(BlockState(((x, y), (x + 1, y)), Orientation.HORIZONTAL))
            if (x, y + 1) in position_set:
                blocks.append(BlockState(((x, y), (x, y + 1)), Orientation.VERTICAL))

        for first, second in combinations(positions, 2):
            for active_cube in (0, 1):
                blocks.append(BlockState.split((first, second), active_cube))

        predecessors = defaultdict(list)
        distance = {}
        queue = deque()
        for block in blocks:
            state = GameState(block, open_bridges)
            if not rules.is_valid(state):
                continue
            if block.is_standing() and isinstance(relaxed_board.get_tile(block.positions[0]), Goal):
                distance[block] = 0
                queue.append(block)
            for action in Move:
                next_state = rules.apply_action(state, action)
                if next_state is not None:
                    predecessors[next_state.block].append(block)

        while queue:
            block = queue.popleft()
            for previous in predecessors[block]:
                if previous not in distance:
                    distance[previous] = distance[block] + 1
                    queue.append(previous)
        return distance


    def solve(self, initial_state):
        pq = PriorityQueue()
        counter = 0
        heuristic_scr = self._heuristic_function(initial_state)
        cur_node = SearchNode(
            state=initial_state, 
            parent=None, 
            action=None, 
            depth=0, 
            path_cost=0
        )
        g_score = {}
        g_score[cur_node.state] = 0 
        pq.put((heuristic_scr, counter, cur_node))

        while not pq.empty(): 
            _, _, state_node = pq.get()
            if g_score[state_node.state] < state_node.path_cost:
                continue

            if self.rules.is_goal(state_node.state):
                return self.reconstruct_path(state_node)

            actions = self.rules.get_valid_actions(state=state_node.state)

            for action in actions: 
                new_state = self.rules.apply_action(state_node.state, action)
                new_g = state_node.path_cost + 1
                if new_g >= g_score.get(new_state, math.inf):
                    continue

                g_score[new_state] = new_g

                new_node = SearchNode(
                    state=new_state, 
                    parent=state_node, 
                    action=action, 
                    depth=state_node.depth + 1, 
                    path_cost=new_g
                )

                f_cost = self._heuristic_function(new_state) + new_node.path_cost
                counter += 1
                pq.put((f_cost, counter, new_node))

        return None
