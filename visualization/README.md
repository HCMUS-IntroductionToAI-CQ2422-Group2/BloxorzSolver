# Bloxorz benchmark visualization

Mở [`benchmark_results.ipynb`](benchmark_results.ipynb) để xem notebook đã chạy,
có sẵn bảng tổng hợp, 7 biểu đồ và diễn giải bằng tiếng Việt. Notebook phân tích
CSV hiện có, **không chạy lại solver** và không thay đổi dữ liệu benchmark.

## Nội dung 7 biểu đồ

1. **Heatmap thời gian theo map và thuật toán**: tìm map tốn thời gian; màu log,
   giá trị ô tính bằng giây.
2. **Boxplot + từng điểm thời gian**: phân bố trên 20 map, thể hiện cả median và
   từng quan sát. Không phải phân bố nhiều lần chạy cùng một map.
3. **Boxplot + từng điểm bộ nhớ**: peak Python allocations tính bằng MiB,
   không gọi nhầm là tổng RAM.
4. **Đồ thị node mở rộng**: so sánh mức tìm kiếm theo map; gộp BFS/UCS thành
   một đường chỉ khi dữ liệu chứng minh hai chuỗi trùng hoàn toàn.
5. **Dumbbell độ dài lời giải**: đối chiếu DFS với BFS/UCS/A*, ghi cả số bước
   và hệ số đường đi dài hơn.
6. **Scatter node–thời gian**: xem quan hệ giữa lượng tìm kiếm và thời gian
   tổng, bao gồm chi phí chuẩn bị heuristic của A*.
7. **Heatmap tỷ lệ so với BFS**: chia từng metric cho BFS trên cùng map rồi
   lấy median của 20 tỷ lệ; 1× là ngang BFS, thấp hơn là tốt hơn. Không gộp
   thành điểm xếp hạng hoặc dùng trọng số tùy ý.

Mỗi biểu đồ có trục/đơn vị, nguồn và ghi chú phương pháp. Màu thuật toán nhất
quán; hình được xuất cả PNG và SVG trong [`figures/`](figures/) để đưa vào báo cáo.

## Cài và chạy lại

Python **3.12 trở lên**; đã thực thi bằng Python 3.14.7. Dùng môi trường riêng,
không cài chung với `requirements.txt` cũ của phần game/report:

```sh
# Chạy từ thư mục gốc repository
python3 -m venv visualization/.venv
source visualization/.venv/bin/activate
# Windows PowerShell: visualization\.venv\Scripts\Activate.ps1
python -m pip install -r visualization/requirements.txt
python -m notebook visualization/benchmark_results.ipynb
```

Trong VS Code cũng có thể mở notebook, chọn Python của môi trường vừa tạo và
**Run All**. Notebook tự tìm CSV từ thư mục gốc hoặc thư mục `visualization`.

Chạy toàn bộ notebook bằng terminal và lưu lại output:

```sh
python -m jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.timeout=180 visualization/benchmark_results.ipynb
```

## Cấu trúc và kiểm chứng

- `benchmark_results.ipynb`: notebook chính, có output đã thực thi.
- `benchmark_plots.py`: đọc/kiểm tra schema, tạo bảng tổng hợp, tính tỷ lệ ghép
  theo map và vẽ 7 biểu đồ bằng Pandas/Matplotlib.
- `requirements.txt`: phiên bản thư viện của môi trường đã kiểm tra.
- `checks.py`: kiểm chứng phép tổng hợp và tỷ lệ ghép map, từ chối dữ liệu
  trùng/thiếu, trộn run hoặc lời giải không hợp lệ. Chạy từ gốc repository:
  `python -m unittest visualization.checks -v`.
- `figures/01_*.png` … `07_*.png` và `.svg`: hình xuất từ chính notebook.

Nguồn: [`../benchmarks/benchmark_20_maps.csv`](../benchmarks/benchmark_20_maps.csv),
schema [`v1.0.0`](../docs/benchmark_csv_schema.md), code solver `29f2323`.
Notebook xác nhận đủ 80 dòng, không trùng khóa, đủ 20 map × 4 thuật toán,
nguồn/môi trường/giới hạn đồng nhất, lời giải đã qua replay và độ dài khớp
chuỗi hành động. Loader báo lỗi nếu thiếu phép đo hoặc có run thất bại; không
âm thầm bỏ dữ liệu, trộn nhiều run hay thay giá trị thiếu bằng 0.

Các cờ replay được kiểm tra từ CSV; notebook không tái thực thi luật chơi.
Bước replay độc lập đã được thực hiện khi tạo CSV, như tài liệu schema mô tả.

## Giới hạn khi diễn giải

- Mỗi map–thuật toán chỉ đo **một lần**. Median/boxplot phản ánh khác biệt
  giữa **các map**, không phải khoảng tin cậy hay độ ổn định qua nhiều lần chạy.
- A* có tính thời gian và bộ nhớ dựng heuristic. Node mở rộng chỉ đếm giai
  đoạn tìm kiếm, không đếm tiền xử lý. Vì vậy ít node hơn chưa chắc nhanh hơn.
- Mọi hành động có chi phí 1, kể cả `switch`. DFS không bảo đảm đường đi ngắn nhất.
- Trục log được ghi rõ; đường nối map chỉ hỗ trợ đọc các hạng mục, không thể
  hiện chuỗi thời gian hay khẳng định độ khó tăng dần theo số map.
- Các tỷ lệ được ghép theo cùng map trước khi tổng hợp. Không kết luận thuật
  toán tốt nhất trong mọi trường hợp hoặc suy ra quan hệ nhân quả từ scatter.
