# Benchmark CSV — schema 1.0.0

File dữ liệu: [`benchmarks/benchmark_20_maps.csv`](../benchmarks/benchmark_20_maps.csv).

Một dòng là **một lần chạy một thuật toán trên trạng thái khởi tạo của một map**.
Khóa duy nhất: **`(run_id, map_id, algorithm, trial)`**.
Bộ dữ liệu này gồm 80 dòng: 20 map × 4 thuật toán × 1 lần chạy.

## Định dạng cố định

- UTF-8 không BOM, dấu phẩy phân cách, dòng kết thúc CRLF, một dòng header.
- Dùng quy tắc quote CSV: trường chứa dấu phẩy, quote hoặc xuống dòng được bọc
  bằng `"`; quote bên trong được viết thành `""`.
- Tên và thứ tự 21 cột dưới đây là cố định cho phiên bản `1.0.0`.
- Số thập phân dùng dấu chấm, không có dấu phân cách hàng nghìn hoặc đơn vị
  trong ô. CSV không mang kiểu dữ liệu; bên đọc cần ép kiểu theo bảng này.
- Boolean viết `true` / `false`. Ô trống của trường nullable là `null`,
  **không phải 0**. Không dùng chuỗi `None`, `NaN` hoặc `N/A`.
- `actions` và `message` dùng chuỗi rỗng khi không có nội dung.

## Các cột

| # | Cột | Kiểu khi đọc | Nullable | Ý nghĩa / ràng buộc |
|---|---|---|---|---|
| 1 | `schema_version` | string | Không | Chính xác `1.0.0`. |
| 2 | `run_id` | string (UUID) | Không | ID chung của một đợt benchmark. |
| 3 | `started_at_utc` | datetime ISO 8601 | Không | Thời điểm bắt đầu từng lượt, timezone `+00:00`. |
| 4 | `git_commit` | string | Không | SHA Git 40 ký tự của code solver được đo. |
| 5 | `map_id` | string | Không | `map01` … `map20`. |
| 6 | `algorithm` | enum | Không | `BFS`, `DFS`, `UCS`, `A*`; dùng đúng `UCS`, không dùng `ÚC`. |
| 7 | `trial` | integer | Không | Số thứ tự lượt lặp, bắt đầu từ 1; bộ hiện tại đều là 1. |
| 8 | `status` | enum | Không | `solved`, `no_solution`, `limit`, `error`. |
| 9 | `search_time_s` | number ≥ 0 | Có | Thời gian do Benchmark đo, đơn vị giây. Null nếu worker không trả được số liệu. |
| 10 | `peak_memory_bytes` | integer ≥ 0 | Có | Đỉnh cấp phát Python do `tracemalloc`, đơn vị byte; không phải RSS. |
| 11 | `expanded_nodes` | integer ≥ 0 | Có | Node thực sự sinh successors; bỏ node đích, heap entry cũ và bước tiền xử lý heuristic. |
| 12 | `solution_length` | integer ≥ 0 | Có | Số hành động của lời giải; chỉ có giá trị khi `status=solved`. |
| 13 | `path_cost` | integer ≥ 0 | Có | Tổng chi phí; bằng `solution_length` vì mỗi hành động đều tốn 1. |
| 14 | `solution_valid` | boolean | Có | Kết quả replay độc lập; null nếu không có lời giải để kiểm chứng. |
| 15 | `time_limit_s` | number > 0 | Không | Giới hạn thời gian nội bộ mỗi lượt; bộ hiện tại là `30`. |
| 16 | `max_nodes` | integer ≥ 0 | Không | Giới hạn node mở rộng; bộ hiện tại là `150000`. |
| 17 | `actions` | string | Không | Các từ `up down left right switch`, phân cách bởi một dấu cách; theo thứ tự thực thi. |
| 18 | `message` | string | Không | Lý do giới hạn/lỗi; chuỗi rỗng nếu không có thông báo. |
| 19 | `python_version` | string | Không | Phiên bản Python dùng để đo. |
| 20 | `platform` | string | Không | Nền tảng và kiến trúc máy chạy benchmark. |
| 21 | `maps_sha256` | string | Không | SHA-256 64 ký tự của `BackEnd/maps/maps.json` tại thời điểm chạy. |

## Quy tắc trạng thái và kiểm chứng

- `solved`: có chuỗi lời giải; `solution_length = path_cost = số token actions`.
  Lời giải hợp lệ cần `solution_valid=true` sau khi replay tới goal.
  Nếu đầu vào đã ở đích: độ dài và chi phí bằng 0, actions rỗng nhưng valid vẫn true.
- `no_solution`: đã duyệt hết không gian tìm kiếm mà không tới đích.
- `limit`: dừng vì giới hạn thời gian hoặc số node; **không kết luận vô nghiệm**.
- `error`: lỗi solver hoặc worker.
- Với ba trạng thái không solved: `solution_length`, `path_cost`,
  `solution_valid` là null; `actions` rỗng. Số liệu đo được vẫn được giữ.
- `solution_valid=false` nghĩa là solver báo solved nhưng replay thất bại;
  dòng đó phải bị đánh dấu kiểm chứng thất bại, không tính là giải thành công.
- Worker chết hoặc vượt deadline ngoài: trường thời gian/node/bộ nhớ không
  lấy được phải là null, không thay bằng 0 hoặc thời gian chờ của tiến trình cha.

## Phương pháp đo của bộ dữ liệu này

- Code solver: commit `29f232303ee2dd234edfcc6580aa3c415b5428c6`
  trên nhánh `feat/hoan-thien-ui` (PR #13). Không đo bản `main` trước khi tích hợp UI.
- Máy: macOS 26.6.2 ARM64, Python 3.14.7. Thời điểm từng lượt được lưu trong CSV.
- Chạy map01 → map20; với mỗi map, chạy BFS → DFS → UCS → A*.
  Chạy **tuần tự**, mỗi lượt dùng một tiến trình `spawn` mới và `init_map()` mới.
- Giới hạn nội bộ 30 giây / 150.000 node. Tiến trình cha có deadline 35 giây
  kể cả chi phí khởi động để có thể dừng worker không phản hồi.
- Dùng `Benchmark` hiện có. Thời gian gồm kiểm tra đầu vào, khởi tạo solver,
  tìm kiếm và dựng heuristic A*. Bao gồm overhead của `tracemalloc`; không gồm
  load map, khởi động tiến trình, UI, truyền kết quả hoặc replay kiểm chứng.
- Peak memory là số byte Python được theo dõi trong lượt chạy, gồm tiền xử lý A*.
  Đổi sang MiB khi hiển thị bằng `peak_memory_bytes / 1048576`.
- Replay chạy ngoài khoảng đo bằng `GameRules.apply_action()` và `is_goal()`.
  Không sửa luật chơi, heuristic hoặc solver để cải thiện số liệu.
- Mỗi cặp chỉ chạy **một lần**; đây là số đo thô, không phải trung bình hoặc
  median nhiều lần chạy. Không kết luận hiệu năng thống kê từ chênh lệch nhỏ.

## Kết quả kiểm tra bộ dữ liệu

- Đủ 80 khóa duy nhất, mỗi thuật toán có đủ 20 map.
- 80/80 dòng `solved`; 80/80 lời giải replay hợp lệ.
- Mỗi map có cùng độ dài lời giải giữa BFS, UCS và A*.
- DFS chỉ yêu cầu đường đi hợp lệ, không bảo đảm ít bước nhất.

Schema này dành cho **benchmark hàng loạt** và có thêm metadata để tái lập phép đo.
CSV xuất từ nút UI hiện tại vẫn dùng schema cũ; không nối hai loại file theo vị trí
cột. Khi tích hợp sau này, writer UI cần xuất đúng header v1.0.0 hoặc chuyển đổi có
kiểm chứng. Không đổi ý nghĩa/kiểu/đơn vị của cột mà giữ nguyên `schema_version`.
