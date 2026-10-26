from collections import deque
from BackEnd.Solver.BaseSolver import BaseSolver
from BackEnd.Solver.SearchNode import SearchNode
from BackEnd.objects.blocks import GameState

class BFSSolver(BaseSolver):
    algorithm_name = "BFS"

    def solve(self, initial_state: GameState):
        goal_node, _ = self._search(initial_state)
        return self.reconstruct_path(goal_node) if goal_node is not None else None

    def _search(self, initial_state: GameState) -> tuple[SearchNode | None, int]:
        expanded_nodes = 0
        
        # Khởi tạo Node gốc
        initial_node = SearchNode(
            state=initial_state,
            parent=None,
            action=None,
            path_cost=0,
        )
        
        queue = deque([initial_node])
        
        # Lưu các trạng thái đã duyệt (Cycle Detection)
        visited = set()
        visited.add(initial_state)

        while queue:
            current_node = queue.popleft()
            
            # Check lọt is_goal
            if self.rules.is_goal(current_node.state):
                # Trả về Node đích và số lượng node đã mở rộng
                return current_node, expanded_nodes
            
            expanded_nodes += 1
            
            # Quét các nhánh con bằng hàm successors có sẵn từ sếp BaseSolver
            for action, next_state, cost in self.successors(current_node.state):
                if next_state not in visited:
                    visited.add(next_state)
                    
                    # Gói nó thành SearchNode mới
                    child_node = SearchNode(
                        state=next_state,
                        parent=current_node,
                        action=action,
                        path_cost=current_node.path_cost + cost,
                        depth=current_node.depth + 1,
                    )
                    queue.append(child_node)

        # Không có đường đi
        return None, expanded_nodes
