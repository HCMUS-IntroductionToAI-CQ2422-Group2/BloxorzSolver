# Method đề xuất cho Tile, Bridge, Switch, BlockState

## Tile

| Method | Chức năng |
| --- | --- |
| `get_positions(self) -> tuple[Position, ...]` | Trả `((self.y, self.x),)` theo `Position = (row, col)`; `x` là cột, `y` là hàng. |
| `can_support(self, block: BlockState, state: GameState) -> bool` | Kiểm tra ô có thể đỡ block hay không. |

Override `can_support()`: `FloorTile`, `Goal` trả `True`; `EmptyCell` trả `False`; `FragileTile` trả `False` khi block đứng thẳng (luật đề xuất).

## Bridge — kế thừa Tile

| Method | Chức năng |
| --- | --- |
| `get_positions(self) -> tuple[Position, ...]` | Override: trả các ô cầu chiếm theo `(x, y, w, h)`. |
| `is_open(self, state: GameState) -> bool` | Trả `self.bridge_id in state.open_bridges`. |
| `can_support(self, block: BlockState, state: GameState) -> bool` | Override: trả `is_open(state)`; cầu mở được hiểu là đi qua được. |

Trạng thái cầu nằm trong `GameState`; thao tác mở/đóng/toggle do `GameRules` xử lý.

## Switch — kế thừa Tile

| Method | Chức năng |
| --- | --- |
| `is_activated(self, block: BlockState) -> bool` | Kiểm tra block có đáp ứng điều kiện kích hoạt switch. |

Điều kiện đề xuất cho `is_activated()`:

- `SoftSwitch`: có vị trí của block trùng ô switch.
- `HeavySwitch`: block đứng thẳng trên ô switch.
- `SplitSwitch`: block đứng thẳng trên ô switch.

Kế thừa `get_positions()` từ `Tile`; `can_support()` trả `True`. `is_activated()` chỉ kiểm tra điều kiện; `GameRules` đọc `effects` hoặc `teleport_positions` để cập nhật trạng thái.

## BlockState — biểu diễn block hiện tại

| Method | Chức năng |
| --- | --- |
| `occupies(self, position: Position) -> bool` | Kiểm tra `position in self.positions`; dùng khi xét switch hoặc ô đặc biệt. |
| `is_standing(self) -> bool` | Kiểm tra `self.orientation == Orientation.STANDING`; dùng cho ô yếu và switch nặng. |
| `is_split(self) -> bool` | Kiểm tra `self.orientation == Orientation.SPLIT`; dùng khi điều khiển từng cube. |

Đọc trực tiếp `positions` và `active_cube`, không cần getter. Giữ `BlockState` bất biến; di chuyển, tách/gộp và đổi cube do `GameRules` xử lý rồi tạo trạng thái mới. Chưa cần class `Block` riêng.
