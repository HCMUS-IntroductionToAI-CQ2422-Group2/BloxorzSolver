from BackEnd.Solver.BaseSolver import BaseSolver
from BackEnd.objects.sharing import Move
from BackEnd.Solver.SearchNode import SearchNode
from BackEnd.logic.game_rules import GameRules
from BackEnd.objects.blocks import GameState
from BackEnd.logic.board import Board
import math
from queue import PriorityQueue

class AStarSolver(BaseSolver): 
    def __init__(self, rules):
        super().__init__(rules)
        
    def _heuristic_function(self, state: GameState):
        if not state.block.is_split(): 
            x_block, y_block = state.block.positions[0]

            return math.sqrt((self.x_goal-x_block)*(self.x_goal-x_block) + (self.y_goal-y_block)*(self.y_goal-y_block))

        else: 
            x_block1, y_block1 = state.block.positions[0]
            x_block2, y_block2 = state.block.positions[1] 

            distance1 = math.sqrt((self.x_goal-x_block1)*(self.x_goal-x_block1) + (self.y_goal-y_block1)*(self.y_goal-y_block1))
            distance2 = math.sqrt((self.x_goal-x_block2)*(self.x_goal-x_block2) + (self.y_goal-y_block2)*(self.y_goal-y_block2))

            return min(distance1, distance2)


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