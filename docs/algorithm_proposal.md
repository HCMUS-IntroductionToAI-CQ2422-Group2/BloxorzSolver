# Bloxorz Solver – Đặc tả bài toán Search

## 1. Phát biểu bài toán

**Yêu cầu:** Với một màn chơi Bloxorz, tìm chuỗi hành động hợp lệ đưa khối từ trạng thái ban đầu đến ô đích. Trạng thái chiến thắng yêu cầu **khối nguyên vẹn đứng thẳng trên ô đích**. BFS, UCS và A* (với heuristic phù hợp) hướng đến lời giải ít hành động nhất; DFS chỉ cần tìm lời giải hợp lệ.

Mô hình hóa bài toán: **\(P = (S, s_0, A, T, G, c)\)**.

| Thành phần | Định nghĩa thống nhất |
|---|---|
| **State \(S\)** | `GameState(block, open_bridges)`, trong đó `block = BlockState(positions, orientation, active_cube)`. `orientation` gồm `STANDING`, `HORIZONTAL`, `VERTICAL`, `SPLIT`; `open_bridges` chứa ID các cầu đang mở. |
| **Initial State \(s_0\)** | `board.game_state` sau khi gọi `init_map(map_name)`. Khối ban đầu đứng thẳng; trạng thái cầu lấy từ `initial_open`. |
| **Actions \(A\)** | `UP`, `DOWN`, `LEFT`, `RIGHT`, `SWITCH`. `SWITCH` chỉ hợp lệ khi khối tách và dùng để đổi khối đang điều khiển. |
| **Transition \(T(s,a)\)** | `rules.apply_action(s, a)` trả về `GameState` mới hoặc `None` nếu không hợp lệ. Hàm này xử lý lăn khối, công tắc, cầu, tách và hợp nhất khối. |
| **Goal Test \(G(s)\)** | `rules.is_goal(s)`: trạng thái hợp lệ và khối **đứng thẳng** tại ô đích. |
| **Step Cost \(c\)** | Mọi hành động hợp lệ có chi phí **1**, kể cả `SWITCH`. Do đó `path_cost = len(actions)`. |

**Quy tắc chung:**
- Dùng trực tiếp `GameState` làm khóa `visited`/`best_cost`. Không chỉ lưu tọa độ: **hướng khối, khối đang điều khiển và trạng thái cầu** đều ảnh hưởng đến các bước tiếp theo.
- Chỉ sinh trạng thái kế tiếp bằng `GameRules.apply_action()`; không viết lại luật chơi trong từng thuật toán.
- Một hành động không hợp lệ (`None`) **không** được thêm vào Frontier.
- Thống nhất thứ tự duyệt: `UP → DOWN → LEFT → RIGHT → SWITCH`. Với DFS dùng stack, lưu ý thứ tự `push` ngược nếu muốn mở rộng theo thứ tự này.
- Giải từ cùng một `initial_state` khi so sánh thuật toán; không thay đổi `Board` hoặc State đầu vào trong quá trình tìm kiếm.

## 2. Các class OOP cần cài đặt thêm

| Class | Trách nhiệm chính |
|---|---|
| `SearchNode` (`dataclass`) | Lưu `state`, `parent`, `action`, `g_cost`, `depth` để truy vết lời giải. |
| `SearchResult` (`dataclass`) | Lưu `algorithm`, `status`, `actions`, `expanded_nodes`, `search_time_s`, `peak_memory_bytes` (nếu đo). `path_cost = len(actions)` khi giải thành công. |
| `BaseSolver` | Chứa `rules: GameRules`, hàm sinh successors, hàm truy vết đường đi và hook đo lường; `BackEnd.search.solve()` chuẩn hóa kết quả thành `SearchResult` cho UI. |
| `BFSSolver` | Cài BFS với FIFO queue. |
| `DFSSolver` | Cài DFS với LIFO stack và chống lặp trạng thái. |
| `UCSSolver` | Cài UCS với priority queue ưu tiên `g_cost`; lưu chi phí tốt nhất theo State. |
| `AStarSolver` | Cài A* với priority queue ưu tiên `f = g + h`; lưu chi phí tốt nhất theo State và hỗ trợ cập nhật đường đi tốt hơn. |

> `SearchNode` và `SearchResult` là cấu trúc dữ liệu dùng chung. Không cần tạo lại `Board`, `BlockState`, `GameState`, `Move` hoặc `GameRules`.

## 3. Các hàm cần sử dụng / cài đặt

### 3.1. Hàm có sẵn trong repository

```python
from BackEnd.init_map import init_map
from BackEnd.logic.game_rules import GameRules
from BackEnd.objects.sharing import Move

board = init_map("map01")
rules = GameRules(board)
initial_state = board.game_state

rules.apply_action(state, action)  # GameState mới hoặc None
rules.get_valid_actions(state)    # Danh sách Move hợp lệ
rules.is_valid(state)             # Kiểm tra State hợp lệ
rules.is_goal(state)              # Kiểm tra thắng
```

### 3.2. Hàm nhóm cần cài đặt

```python
class BaseSolver:
    def __init__(self, rules: GameRules): ...

    def successors(self, state):
        """Sinh (action, next_state, cost=1) theo thứ tự chung."""
        for action in (
            Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT, Move.SWITCH
        ):
            next_state = self.rules.apply_action(state, action)
            if next_state is not None:
                yield action, next_state, 1

    def reconstruct_path(self, goal_node):
        """Lần theo parent để trả về list[Move] từ đầu đến đích."""
        ...

    def solve(self, initial_state):
        """BFS/UCS/A*: list[Move] hoặc None; DFS: SearchResult."""
        raise NotImplementedError

class AStarSolver(BaseSolver):
    def heuristic(self, state) -> float:
        """Ước lượng chi phí còn lại; mặc định có thể dùng h=0."""
        return 0
```

**Giao diện gọi thống nhất:**

```python
from BackEnd.search import solve

result = solve(board, initial_state, "BFS")  # Hoặc DFS / UCS / A*
# Gọi trực tiếp BFS/UCS/A* trả list[Move] | None:
actions = BFSSolver(rules).solve(initial_state)
# DFS giữ API SearchResult của main:
dfs_result = DFSSolver(rules).solve(initial_state)
```

**Quy ước kết quả và đo lường:**
- `status`: `solved`, `no_solution`, `limit` hoặc `error`; không coi hết thời gian là vô nghiệm.
- `actions`: `list[Move]`, gồm cả `SWITCH`; phải replay được từ State đầu vào và kết thúc với `rules.is_goal(state) == True`.
- `expanded_nodes`: số Node thực sự mở rộng (sinh successors), không tính entry cũ/trùng bị bỏ qua.
- BFS/UCS phải cho **cùng độ dài lời giải tối ưu** vì mọi bước có chi phí 1. A* chỉ được khẳng định tối ưu khi heuristic và cách xử lý Frontier bảo đảm tính tối ưu; `h=0` là lựa chọn cơ sở an toàn.

**Kiểm thử:** chạy lại chuỗi `actions` qua `apply_action()` và xác nhận Goal; kiểm tra thêm các màn có cầu/công tắc (`map02`), ô dễ vỡ (`map04`) và tách khối (`map09`).

## 4. UCS – triển khai hiện tại

`BackEnd/Solver/UCSSolver.py` dùng min-heap ưu tiên `SearchNode.path_cost`
(tương ứng `g_cost` trong đặc tả). `best_cost` lưu chi phí thấp nhất theo toàn bộ
`GameState`; chỉ thêm đường đi tốt hơn và bỏ qua entry cũ khi lấy khỏi heap.
Kiểm tra đích khi lấy Node ra khỏi heap. Bộ đếm thứ tự giúp xử lý các Node cùng
chi phí theo thứ tự thêm, không cần so sánh trực tiếp các State.

UCS dùng `BaseSolver.successors()` và `reconstruct_path()`. Mỗi hành động có
chi phí 1, kể cả `SWITCH`, nên lời giải có số hành động ít nhất.

**Giao diện hiện tại:** giống A*, `solve()` trả về `list[Move]` khi tìm được
lời giải, `[]` nếu đầu vào đã ở đích, hoặc `None` nếu không có lời giải.
`BackEnd.search.solve()` bọc lời gọi solver bằng `Benchmark` và trả về
`SearchResult` có số liệu đo lường cho GUI. UCS đã được nối vào chế độ
**Solve by algorithm** cùng BFS, DFS và A*.

```python
from BackEnd.Solver.UCSSolver import UCSSolver

board = init_map("map09")
rules = GameRules(board)
actions = UCSSolver(rules).solve(board.game_state)
```

Chạy kiểm thử bằng `python -m pytest tests/test_ucs.py -q`: đối chiếu độ dài
với BFS và replay lời giải trên các map 01, 02, 04, 08, 09; kiểm tra trạng thái
đã thắng, màn vô nghiệm có chu trình và cập nhật đường đi có chi phí tốt hơn.

## 5. Benchmark và tích hợp UI

`Benchmark` trong `BackEnd/Benchmark.py` chuẩn hóa ý tưởng hàm bọc `solve()`
đo thời gian / `tracemalloc` ở nhánh BFS/Benchmark của nhóm. Mỗi lần chạy tạo
solver mới, đo cả khởi tạo và tìm kiếm, bao gồm dựng bảng heuristic của A*.
Kết quả dùng chung class `SearchResult` tại `BackEnd/Solver/SearchResult.py`.
Wrapper nhận cả danh sách hành động từ BFS/UCS/A* và `SearchResult` từ DFS;
giữ nguyên trạng thái lỗi/vô nghiệm của DFS và phân biệt việc dừng do giới hạn.
`BaseSolver.successors()` ghi nhận số node mở rộng; các vòng tiền xử lý của A*
kiểm tra thời hạn nhưng không cộng vào số node mở rộng của tìm kiếm.

- `search_time_s`: giây, dùng `perf_counter`; gồm overhead của `tracemalloc`.
- `peak_memory_bytes`: đỉnh cấp phát Python, không phải tổng RAM của tiến trình.
- `expanded_nodes`: số lần thực sự sinh successors, không tính node đích hoặc
  entry cũ của priority queue.
- `path_cost`: `len(actions)` khi `solved`; `None` ở các trạng thái khác.
- `status`: `solved`, `no_solution`, `limit`, `error`; `message` nêu lý do dừng.

UI chạy solver trong tiến trình `spawn` riêng, giới hạn 30 giây / 150.000 node.
Cancel, Esc, đổi màn, restart hoặc trở về chế độ thủ công sẽ dừng worker.
Nếu worker bị lỗi hoặc bị cưỡng chế dừng bởi deadline của UI, số liệu node và
bộ nhớ không thu được sẽ là `None`, không ghi thành số 0.

Chọn **Solve by algorithm → thuật toán → Run** để chạy từ trạng thái hiện tại.
**Replay / Step** phát lại từ trạng thái bắt đầu; **Export CSV** lưu benchmark
cùng map, trạng thái và chuỗi hành động. Restart trước các lượt chạy để so sánh
cùng đầu vào. Chế độ solver mở toàn bộ 20 màn nhưng không ghi sao hay tiến độ
chiến dịch; DFS chỉ bảo đảm lời giải hợp lệ, không bảo đảm ngắn nhất.
