# TASK: Cài đặt phần Switch + Block cho Bloxorz engine

Đọc `CONTEXT.md` trước (glossary: Block, Cube, Split mode, Landing, Activation, Supported, Merge). Mọi thuật ngữ trong file này dùng đúng nghĩa trong glossary.

## 1. Phạm vi

**Làm:** cơ chế block, cube, switch, bridge trong `objects.py` và `game_engine.py` (lớp `GameRules`).

**Không làm (người khác phụ trách):** các solver (BFS/DFS/UCS/A*), `SearchProblem`/`SearchResult`, cost function, heuristic, GUI, định dạng file stage. Không sửa code search. Nếu cần thay đổi giao diện chung, ghi vào mục "Vấn đề cần báo lại" ở cuối thay vì tự sửa.

## 2. Quy ước chung

- Mọi state **bất biến và hashable** (`frozen=True`). Không mutate, luôn tạo state mới.
- `GameRules` là **hàm thuần**: cùng `(state, action)` luôn cho cùng kết quả, không có trạng thái ẩn, không random.
- Tập action: `UP`, `DOWN`, `LEFT`, `RIGHT`, `SWITCH`. Dùng enum `Move` (thêm `SWITCH`), không dùng string tự do.
- `apply_action` trả `None` nếu nước đi illegal. `get_valid_actions` chỉ trả action cho ra state hợp lệ.
- Tọa độ: xem mục "Giả định mặc định" số 1.

## 3. State

```
GameState(block: BlockState, open_bridges: frozenset[str])
BlockState(positions: tuple[Position, ...], orientation: Orientation, active_cube: int = 0)
```

| Chế độ | `orientation` | `positions` | `active_cube` |
|---|---|---|---|
| Đứng | `STANDING` | 1 ô | 0 |
| Nằm ngang | `HORIZONTAL` | 2 ô kề ngang, sắp xếp tăng | 0 |
| Nằm dọc | `VERTICAL` | 2 ô kề dọc, sắp xếp tăng | 0 |
| Split | `SPLIT` | 2 ô (hai cube), **sắp xếp tăng** | 0 hoặc 1 |

**Chuẩn hóa (bắt buộc):** trong chế độ split, `positions` luôn sắp xếp tăng dần. Nếu việc sắp xếp hoán đổi hai cube thì đổi `active_cube` tương ứng (ví dụ `active_cube` 0 thành 1). Mục đích: `{A, B}` và `{B, A}` là cùng một state. Viết **một** hàm tạo state split duy nhất làm việc này và dùng ở mọi nơi.

`open_bridges` chứa `bridge_id` của các cầu đang mở. Trạng thái ban đầu: các cầu có `initial_open=True`. Thêm hàm `initial_state(board) -> GameState`: block đứng tại `board.start_position`, `open_bridges` như trên.

## 4. Bảng chuyển orientation (`_roll`)

Gọi `(r, c)` là hàng, cột; `UP` giảm `r`, `LEFT` giảm `c`. Với block nằm, `(r, c)` là ô nhỏ hơn.

| Orientation hiện tại | UP | DOWN | LEFT | RIGHT |
|---|---|---|---|---|
| STANDING `(r,c)` | VERTICAL `(r-2,c),(r-1,c)` | VERTICAL `(r+1,c),(r+2,c)` | HORIZONTAL `(r,c-2),(r,c-1)` | HORIZONTAL `(r,c+1),(r,c+2)` |
| HORIZONTAL `(r,c),(r,c+1)` | HORIZONTAL, `r-1` | HORIZONTAL, `r+1` | STANDING `(r,c-1)` | STANDING `(r,c+2)` |
| VERTICAL `(r,c),(r+1,c)` | STANDING `(r-1,c)` | STANDING `(r+2,c)` | VERTICAL, `c-1` | VERTICAL, `c+1` |

`_roll` chỉ tính hình học, **không** kiểm tra hợp lệ. Ở chế độ split, `_roll` lăn **một cube**: cube `active_cube` dịch một ô theo hướng, cube kia giữ nguyên.

## 5. Thứ tự xử lý trong `apply_action` (quan trọng)

Thực hiện đúng thứ tự này:

1. `SWITCH`: chỉ hợp lệ khi `orientation == SPLIT`. Đổi `active_cube` (0 thành 1 và ngược lại), trả state mới, **dừng** (không landing, không kích hoạt gì).
2. **Lăn** (`_roll`) để có `positions` mới. Tập **landing cells** = toàn bộ ô của phần vừa di chuyển sau lần lăn (với block nguyên: cả hai ô mới, kể cả ô trụ; với cube: ô mới của cube đó). Phần đứng yên không nằm trong landing.
3. **Kiểm tra legal ban đầu** (trạng thái cầu *trước* lần lăn): mọi ô trong bàn, không void, mỗi ô `can_support` đúng, hai cube không trùng ô. Sai thì trả `None`.
4. **Áp dụng switch** (`_apply_switches`) chỉ với các ô trong landing cells (edge-trigger), xem mục 6.
5. **Kiểm tra lại support** (`is_valid`) cho **toàn bộ** phần của block/cube, kể cả cube đứng yên, theo `open_bridges` *sau* bước 4. Sai thì trả `None` (coi như rơi).
6. **Merge** (`_merge_block`): chỉ khi vừa lăn một cube, orientation là `SPLIT` và hai cube ở hai ô kề nhau (khoảng cách Manhattan = 1) thì thành `HORIZONTAL`/`VERTICAL`, `active_cube = 0`. **Không** merge ngay sau teleport.

Teleport và merge không kích hoạt thêm switch nào.

## 6. Switch

`is_activated(block)` chỉ kiểm tra điều kiện; việc áp dụng nằm ở `GameRules`.

| Loại | Điều kiện kích hoạt (cùng với: ô switch nằm trong landing cells) |
|---|---|
| `SoftSwitch` | Bất kỳ phần nào (block hoặc cube) hạ xuống ô đó. |
| `HeavySwitch` | `orientation == STANDING` và vị trí block trùng ô switch. Lăn nằm lên ô đó **không** kích hoạt; cube **không** kích hoạt. |
| `SplitSwitch` | `orientation == STANDING` và vị trí block trùng ô switch. **Cube không kích hoạt** (kể cả khi đứng sẵn trên ô). |

**Effect (`_update_bridges`):** mỗi `SwitchBridgeLink`:
- `TOGGLE`: đảo trạng thái cầu đó (có trong `open_bridges` thì bỏ, chưa có thì thêm).
- `SET`: đặt cầu mở/đóng theo `target_open`. Idempotent, kích hoạt lại không thay đổi.

Nếu một lần lăn kích hoạt nhiều switch, áp dụng effect **theo thứ tự `switch_id` tăng dần** (tất định).

**Split switch (`_split_block`):** ngoài áp dụng `effects` của nó (nếu có), đặt `positions = teleport_positions` (đã chuẩn hóa theo mục 3), `orientation = SPLIT`, `active_cube = 0`. Không kiểm tra merge ngay.

**Ràng buộc nạp stage:** nếu hai ô trong `teleport_positions` của một `SplitSwitch` kề nhau hoặc trùng nhau thì báo lỗi rõ ràng khi dựng `Board`/`GameRules` (lỗi thiết kế level).

## 7. Support và win

- `can_support` theo `objects_methods.md`: `FloorTile`, `Goal` luôn `True`; `EmptyCell` `False`; `FragileTile` `False` khi `block.is_standing()`; `Bridge` trả `is_open(state)`; `Switch` trả `True`.
- Hệ quả mong muốn: ở `SPLIT`, `is_standing()` là `False` nên **cube đứng được trên ô fragile**. Giữ nguyên hành vi này.
- Cầu chiếm vùng `(x, y, w, h)`: cần một cách tra ô thành tile, trong đó ô thuộc cầu phải hỏi `Bridge`, không phải ô nền bên dưới. Viết hàm tra cứu này một lần.
- `is_goal(state)`: `orientation == STANDING` và vị trí trùng `board.goal_position`. Block nằm hoặc cube thì **không** thắng.

## 8. Việc cần làm cụ thể

1. `objects.py`: sửa lỗi dataclass (xem mục 10), thêm các method theo `objects_methods.md`.
2. `game_engine.py`: cài `apply_action`, `get_valid_actions`, `is_valid`, `is_goal`, `_roll`, `_apply_switches`, `_update_bridges`, `_split_block`, `_merge_block`, `_switch_cube`, cùng `initial_state`.
3. `Board` cần là dataclass thật (hiện chỉ có annotation).
4. **Đổi chữ ký** `_apply_switches(old_state, new_state)` thành `_apply_switches(state, landed: tuple[Position, ...]) -> GameState`, vì edge-trigger cần biết ô nào vừa landing.
5. Thêm `Move.SWITCH`.

## 9. Test bắt buộc (pytest, không phụ thuộc GUI)

- **Bảng chuyển:** đủ 12 cặp (orientation × hướng), trên bàn trống đủ rộng.
- **Illegal:** lăn ra ngoài bàn; lăn lên void; đứng trên fragile; hai cube trùng ô.
- **Soft:** block đứng và block nằm đều kích hoạt khi landing.
- **Heavy:** đứng thì kích hoạt, nằm lên thì không, cube thì không.
- **Edge-trigger:** cube A đứng sẵn trên soft switch (toggle); lăn cube B không kích hoạt lại switch của A.
- **Toggle và SET:** `toggle` hai lần trở về trạng thái cũ; `SET` kích hoạt hai lần giữ nguyên.
- **Rơi do cầu đóng:** lăn mà một đầu bấm switch đóng cầu dưới đầu kia thì `apply_action` trả `None`.
- **Cube đứng yên bị cầu đóng dưới chân** (do cube kia bấm) thì `None`.
- **Split:** teleport đúng vị trí, `active_cube = 0`, không merge ngay; `SWITCH` đổi cube; hai cube chuẩn hóa cho cùng hash khi hoán đổi.
- **Merge:** hai cube kề ngang thành `HORIZONTAL`, kề dọc thành `VERTICAL`, `active_cube = 0`; không merge khi cách nhau 2 ô.
- **Split switch:** cube đứng trên ô split switch không kích hoạt.
- **Win:** đứng trên Goal là thắng; nằm trên Goal hoặc cube trên Goal thì không.
- **Tính tất định:** gọi `apply_action` hai lần với cùng đầu vào cho cùng kết quả.

## 10. Lỗi đã nghi ngờ trong code hiện tại (hãy xác minh bằng cách chạy `import`)

- Trong `objects.py`, `Bridge` và `Switch` khai báo field `type: str` (không default) sau field có default, nên khả năng cao gây `TypeError` ngay lúc định nghĩa class. `SplitSwitch` có `type: str` tương tự.
- Các subclass `FloorTile`, `EmptyCell`, `Goal`, `FragileTile`, `SoftSwitch`, `HeavySwitch` gán `type = "..."` ở cấp class nhưng không phải dataclass; constructor kế thừa vẫn đòi tham số `type`. Cần một cách thống nhất để `type` tự điền (ví dụ `field(init=False, default=...)` hoặc `ClassVar`).
- `from .objects import *` và `GameRules` tham chiếu `GameState`, `BlockState`, `Switch`, `SplitSwitch`, `Bridge`, `Tile`: kiểm tra import thật sự chạy.

## 11. Giả định mặc định (dùng nếu không có chỉ dẫn khác; ghi vào mục báo lại nếu phải đổi)

1. **Tọa độ:** `Position = (row, col)`. Với `Tile(x, y)`, coi `x` là cột và `y` là hàng khi tra bàn; tài liệu hóa rõ trong docstring và dùng đúng một quy ước ở mọi nơi.
2. **Landing:** mọi ô của phần vừa lăn đều tính, kể cả ô trụ mà block vừa xoay quanh nó.
3. **Teleport:** `teleport_positions[0]` và `[1]` là vị trí hai cube; sau chuẩn hóa `active_cube = 0`.
4. **Action:** giao diện với solver dùng `Move` (kể cả `SWITCH`); chốt lại với người làm search.

## 12. Vấn đề cần báo lại (điền khi làm)

- Giữ giả định `Position = (row, col)`, `Tile(x, y)` = (cột, hàng). Đã sửa mô tả `get_positions` trong `objects_methods.md` để cùng quy ước.
- `GameRules` nhận/trả action kiểu `Move`, có `Move.SWITCH`. Các khai báo search hiện vẫn dùng `str`; người phụ trách search cần tích hợp theo giao diện `Move`. Không đổi các lớp search trong phần việc này.
- `BlockState.split(positions, active_cube)` chuẩn hóa vị trí và giữ cube đang chọn; teleport chọn cube có vị trí nhỏ hơn (`active_cube = 0`) theo giả định số 3.
- `Tile.type` và các lớp con là thuộc tính lớp tự điền, không còn tham số constructor. `Board.tile_at` là nơi duy nhất tra ô có ưu tiên vùng cầu.
- Import thực tế: `objects.py` cũ import được nhưng constructor vẫn yêu cầu `type`; `game_engine.py` lỗi `SyntaxError` vì future import nằm giữa file. Đã đưa import lên đầu và hỗ trợ cả import trực tiếp lẫn import qua package; phần khai báo search giữ nguyên.
- Code theo task nằm ở root (`objects.py`, `game_engine.py`); các file `BackEnd/objects/` của nhóm giữ nguyên. Nhóm trưởng cần quyết định cách tích hợp khi ghép các phần.

## 13. Kiểm thử phần Switch + Block

Yêu cầu Python >= 3.10. Từ thư mục repo:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Bộ test ở `tests/test_switch_block.py` kiểm tra bảng lăn, support, switch/effect, split/merge, goal, tính bất biến và tất định; không cần GUI hoặc solver.
