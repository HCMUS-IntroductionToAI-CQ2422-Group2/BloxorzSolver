# Báo cáo LaTeX

File chính: `main.tex`. Giữ mẫu FIT–HCMUS trong `fit_hcmus.sty` và biên dịch bằng **pdfLaTeX**.

## Phần nội dung đã bổ sung từ session

- `sections/UCS.tex`: mô hình trạng thái, chi phí, cấu trúc heap, mã giả, tính tối ưu, độ phức tạp và kiểm thử UCS.
- `sections/game_implement.tex`: tích hợp solver vào UI có sẵn, worker, benchmark, replay, CSV và tương thích sau merge.
- `sections/benchmark.tex`: phương pháp đo 20 maps, schema, kết quả, 7 loại biểu đồ và hạn chế; chèn 3 hình tiêu biểu.
- `sections/verification.tex`: kết quả kiểm thử theo từng commit, phạm vi đóng góp và khai báo hỗ trợ AI.
- `sections/01_thong_tin_nhom.tex`: bổ sung mô tả công việc cho Nguyễn Thành Bảo; giữ trống mức độ hoàn thành để nhóm thống nhất.

Các file BFS, DFS, AStar, introduction và project_planning vẫn là phần dành cho nhóm bổ sung. `main.tex` đã nối chúng vào bố cục, cùng các nội dung mới. Không coi bản này là báo cáo đầy đủ của cả nhóm.

## Nguồn số liệu và hình

Bảng số liệu lấy từ `../benchmarks/benchmark_20_maps.csv`: 80 lượt của solver commit `29f2323`, mỗi map–thuật toán chỉ đo một lần. Không trộn với CSV 15 maps mới hoặc gọi đây là kết quả đo main hiện tại.

Ba hình trong `figures/benchmark_*.png` được sao chép nguyên từ `../visualization/figures/04_expanded_nodes.png`, `05_solution_lengths.png` và `07_relative_to_bfs.png`. Giữ hình trong `report/` để có thể tải riêng thư mục này lên công cụ biên dịch LaTeX.

## Biên dịch

Chạy từ thư mục `report/` với TeX Live/MacTeX có hỗ trợ tiếng Việt (`vntex`) và các gói trong `fit_hcmus.sty`:

```sh
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

Hoặc dùng `latexmk -pdf main.tex` nếu đã cài latexmk. Khi tải thư mục lên trình soạn thảo LaTeX, chọn `main.tex` làm tài liệu chính và **pdfLaTeX** làm compiler.

`main.pdf` chỉ phản ánh lần biên dịch cuối cùng, không tự cập nhật khi chỉnh `.tex`. Môi trường soạn bản bổ sung này chưa có pdfLaTeX/BibTeX, nên PDF đang lưu trong repo vẫn là bản cũ; cần biên dịch và xem lại bố cục trước khi nộp.
