import time
import tracemalloc
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

def solve(self, initial_state: GameState):
    """Hàm bọc ngoài để thực hiện đo lường (Benchmark) cho mọi thuật toán."""
    print(f"Bắt đầu chạy thuật toán...")
    
    # 1. Khởi động bộ đo lường
    tracemalloc.start()
    start_time = time.perf_counter()
    
    # 2. Gọi hàm logic lõi (được implement ở các class con như BFS, DFS...)
    # Hàm lõi cần trả về: (Node đích tìm được, Số node đã mở rộng)
    goal_node, expanded_nodes = self._search(initial_state)
    
    # 3. Chốt sổ kết quả đo lường
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    end_time = time.perf_counter()
    
    # Tính toán
    search_time = end_time - start_time
    peak_memory_mb = peak_mem / (1024 * 1024) # Đổi ra Megabyte
    
    # 4. Trả về kết quả chung
    if goal_node:
        actions = self.reconstruct_path(goal_node)
        print(f"✅ Success! Runtime: {search_time:.4f}s | RAM: {peak_memory_mb:.4f}MB | Node mở rộng: {expanded_nodes}")
        return {
            "success": True,
            "actions": actions,
            "search_time": search_time,
            "peak_memory": peak_memory_mb,
            "expanded_nodes": expanded_nodes,
            "solution_length": len(actions),
            # "total_cost": goal_node.cost # Mở comment cái này ra nếu SearchNode của team m có biến lưu cost
        }
    else:
        print("❌ Failed: No solution found!")
        return {
            "success": False,
            "actions": [],
            "search_time": search_time,
            "peak_memory": peak_memory_mb,
            "expanded_nodes": expanded_nodes,
            "solution_length": 0,
            # "total_cost": 0
        }

@abstractmethod
def _search(self, initial_state: GameState) -> tuple[SearchNode | None, int]:
    """
    Logic thuật toán lõi. Các class con (BFSSolver, AStarSolver...) 
    BẮT BUỘC phải ghi đè (override) hàm này thay vì hàm solve.
    Phải trả về 1 tuple gồm: (SearchNode đích, Số lượng node đã mở (int))
    """
    pass