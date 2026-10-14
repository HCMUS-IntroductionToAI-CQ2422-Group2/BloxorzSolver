# Giao diện phần Switch + Block

Phần này chỉ cung cấp mô hình và luật chơi. Solver, GUI, cost function và bộ đọc stage do các thành viên khác triển khai.

## Import chung

```python
from BackEnd import Board, GameRules, Move, initial_state
from BackEnd import BlockState, GameState, Orientation
from BackEnd import FloorTile, EmptyCell, Goal, FragileTile, Bridge
from BackEnd import SoftSwitch, HeavySwitch, SplitSwitch, SwitchBridgeLink, EffectMode
```

Các export trên trỏ đến đúng các lớp trong `BackEnd/objects/blocks.py`, `tiles.py`, `bridges.py`, `switchs.py`, `sharing.py`. Không có bản sao ở root, không có solver hoặc lớp search rỗng. Tên file `switchs.py` được giữ theo main của nhóm.

## Hợp đồng cho GUI và solver

- Tọa độ state là `(row, col)`. Constructor tile dùng `x=col`, `y=row`; `get_positions()` trả `(row, col)`. Không truyền tham số `type` vào constructor.
- `Board(tiles, bridges, start_position, goal_position)` nhận lưới tile và dictionary cầu theo ID. Các container được sao chép sang tuple và mapping chỉ đọc, nên sửa dữ liệu đầu vào không làm luật chơi thay đổi.
- `initial_state(board)` tạo block đứng ở start với các cầu `initial_open=True`. Start không được đỡ sẽ báo `ValueError`.
- `GameRules.apply_action(state, Move.RIGHT)` trả state mới hoặc `None` nếu nước đi illegal. Truyền string thay cho `Move` báo `TypeError` để phát hiện lỗi tích hợp; GUI cần ánh xạ phím thành enum trước khi gọi.
- `get_valid_actions(state)` trả `list[Move]`; `is_valid(state)` kiểm tra hình dạng, ID cầu và support; `is_goal(state)` chỉ đúng khi block hợp lệ đứng trên tọa độ goal.
- `GameState` và `BlockState` bất biến, hashable: solver có thể dùng trực tiếp làm khóa trong visited/parent/cost. `open_bridges` là một phần của state.
- `Move.SWITCH` chỉ dùng trong split mode và không kích hoạt switch trên bàn. Solver quyết định cost của action này; engine không áp đặt cost.
- `BlockState.split(positions, active_cube)` chuẩn hóa thứ tự và giữ đúng cube đang chọn. Teleport chọn cube ở vị trí nhỏ hơn (`active_cube=0`).
- `Board.tile_at(position)` là nơi tra support duy nhất: vùng cầu ưu tiên hơn tile nền. Ngoài bàn trả `None`. Màu/loại tile để vẽ không thay thế việc kiểm tra cầu theo state.

Ví dụ phía gọi (không phải thuật toán search):

```python
rules = GameRules(board)
state = initial_state(board)
for action in saved_actions:  # các phần tử đều là Move
    successor = rules.apply_action(state, action)
    if successor is None:
        raise ValueError("Đường đi không hợp lệ trên board này")
    state = successor
won = rules.is_goal(state)
```

## Kiểm tra dữ liệu stage

Board từ chối lưới rỗng/không chữ nhật, tọa độ tile lệch vị trí trong lưới, start/goal ngoài bàn, bridge ID không khớp dictionary, vùng cầu ngoài bàn/chồng nhau hoặc che switch, switch ID trùng, effect trỏ tới cầu không tồn tại, teleport trùng/kề nhau hoặc ngoài bàn. Đây là kiểm tra mô hình, không định nghĩa JSON hoặc cách nạp stage.

Teleport vào void/cầu đóng được kiểm tra khi thực hiện action, sau khi effect đã áp dụng. Điều này cho phép split switch mở chính cầu đỡ cube ở điểm đến. Teleport và merge không kích hoạt switch dây chuyền.

## Kiểm thử

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Python >= 3.10. `requirements-dev.txt` bao gồm `requirements.txt` và pytest. Người chỉ chạy ứng dụng cài file requirements chính.

- `tests/test_switch_block.py`: hợp đồng luật chơi qua API công khai — bảng lăn, support, landing, toggle/SET, cầu đóng gây rơi, split/merge, goal. Fixture có cầu thật được đăng ký; không dùng effect trỏ tới ID giả.
- `tests/test_integration_contract.py`: xác nhận các đường import dùng cùng lớp, từ chối stage sai, bảo vệ board khỏi thay đổi container bên ngoài, và replay một màn từ start đến goal qua mở cầu → qua cầu → fragile → split → SWITCH → merge. Một consumer thứ hai replay lại cùng action list để kiểm tra không có trạng thái ẩn.

Các test này xác nhận API engine và hành vi của level mẫu; chưa xác nhận GUI, solver, hiệu năng tìm kiếm hoặc định dạng stage vì các phần đó chưa tồn tại. Khi các thành viên tích hợp, cần bổ sung test tại chính phía gọi của họ.
