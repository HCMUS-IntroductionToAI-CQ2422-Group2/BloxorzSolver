# Bloxorz Solver — Glossary

Chỉ chứa thuật ngữ miền bài toán. Không ghi quyết định cài đặt ở đây.

## Block
Khối 1×1×2 do người chơi điều khiển khi chưa bị tách. Luôn ở đúng một trong ba **orientation**: standing, lying horizontally, lying vertically.

## Cube
Khối 1×1×1. Chỉ tồn tại thành cặp, sau khi **Block** bị tách bởi một split switch. Tại mỗi thời điểm người chơi điều khiển đúng một cube.
_Tránh dùng:_ "half-block", "mini block".

## Split mode
Chế độ chơi khi có hai **Cube** thay cho một **Block**. Kết thúc khi hai cube nằm trên hai ô kề nhau và hợp lại thành **Block**.
_Lưu ý:_ Split mode là một chế độ chứ không phải orientation thứ tư của Block.

## Landing
Sự kiện một phần của block hoặc một cube **vừa** hạ xuống một ô sau một lần lăn. Phần không di chuyển thì không có landing.

## Activation (kích hoạt)
Một switch chỉ được kích hoạt khi có **landing** trên ô của nó và thỏa điều kiện của loại switch (soft, heavy, split).
- Cube hoặc block đứng yên sẵn trên switch **không** kích hoạt lại khi cube khác di chuyển.
- Hợp nhất (merge) hai cube không tự kích hoạt switch nào; việc kích hoạt đã xảy ra ở lần lăn tạo ra merge.
- Điểm đến của teleport không kích hoạt dây chuyền.

## Supported (được đỡ)
Mọi phần của block hoặc cube đều nằm trên ô có thể đỡ nó (floor, goal, fragile khi block nằm, cầu đang mở, switch). Một state chỉ **hợp lệ** khi được đỡ ở trạng thái cầu *sau* khi các switch đã có hiệu lực.
- Một lần lăn làm cầu đóng ngay dưới chính nó (hoặc dưới cube đứng yên) khiến state không hợp lệ: coi như rơi, nước đi bị loại.

## Merge (hợp nhất)
Hai **Cube** trở lại thành một **Block** khi sau một lần lăn của cube chúng nằm trên hai ô kề nhau. Merge không xảy ra ngay sau khi tách.
- Hai cube không bao giờ cùng một ô; lăn vào ô của cube kia là illegal.
- Chỉ **Block** đứng thẳng mới kích hoạt split switch; cube thì không.
