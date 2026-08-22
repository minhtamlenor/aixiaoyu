# TIỂU VŨ AI — MASTER RULE

## 1. Mục đích
Đây là luật bảo vệ nền tảng của Tiểu Vũ. Mọi AI/agent khi đọc, sửa hoặc mở rộng repo `aixiaoyu` phải tuân thủ trước khi thay đổi code.

## 2. CẤM ĐỤNG VÀO CODE NỀN ĐANG ỔN
Không tự ý sửa, thay thế, refactor, đổi framework, đổi kiến trúc hoặc nâng/hạ phiên bản đối với các thành phần nền tảng đang chạy ổn, trừ khi Lão sư yêu cầu rõ ràng.

Bao gồm nhưng không giới hạn:
- Framework/runtime và cấu trúc khởi động ứng dụng.
- Cơ chế Gemini Live/API connection đang hoạt động.
- Audio input/output, microphone, speaker, VAD, audio queue và playback.
- Cơ chế Tutor Mode đang hoạt động tốt.
- `tutor/` và các engine nền của gia sư nếu nhiệm vụ không trực tiếp yêu cầu thay đổi chúng.
- Environment/configuration, dependency và package version.
- Các luồng dữ liệu, state machine, session và interface hiện có.
- Các integration/API hiện tại.

## 3. NGUYÊN TẮC MỞ RỘNG
- Ưu tiên tạo module/file mới thay vì sửa code nền.
- Tách feature mới khỏi feature đang ổn định.
- Không thay đổi public interface hoặc behavior cũ nếu không cần thiết.
- Nếu có thể giải quyết bằng adapter, wrapper, hook hoặc module riêng thì dùng cách đó trước.
- Tutor Mode luôn có quyền ưu tiên cao hơn các tính năng Chat Mode.

## 4. DATA FRAMEWORK / CONTENT
Nội dung mới phải được lưu ở lớp dữ liệu riêng, không nhúng hàng loạt nội dung vào prompt hoặc code runtime.

Ví dụ:
- Buddhist stories → `stories/buddhism/`
- Nội dung mới → file Markdown/data riêng.

Thêm nội dung không được yêu cầu sửa framework hoặc engine nền.

## 5. TRƯỚC KHI SỬA CODE
AI phải:
1. Đọc cấu trúc repo.
2. Xác định file nào là nền tảng đang chạy ổn.
3. Tìm đúng runtime path của tính năng cần sửa.
4. Kiểm tra xem có thể thêm module riêng hay không.
5. Không sửa file nền chỉ vì thấy có thể "làm đẹp" hoặc refactor.

## 6. SAU KHI SỬA
Phải kiểm tra:
- Syntax/import.
- Không phá Tutor Mode.
- Không phá Chat Mode hiện tại.
- Không phá audio/live connection.
- Không tạo dependency không cần thiết.
- Commit phải mô tả chính xác thay đổi.

## 7. QUY TẮC KHI CHƯA CHẮC
Nếu một thay đổi có nguy cơ ảnh hưởng code nền hoặc behavior đang ổn định: DỪNG, không tự ý sửa. Báo rõ file, nguy cơ và phương án trước khi thực hiện.

## 8. STATUS COMMIT — BẮT BUỘC
Mỗi lần hoàn thành một thay đổi đáng kể, phải có commit cuối cùng ghi rõ trạng thái.

Format khuyến nghị:

`STATUS: SUCCESS — <mô tả ngắn>`

hoặc

`STATUS: IN_PROGRESS — <mô tả ngắn>`

hoặc

`STATUS: BLOCKED — <mô tả ngắn>`

Commit phải giúp nhìn vào commit cuối cùng là biết ngay:
- Tiểu Vũ vừa được điều chỉnh phần nào.
- Việc đó đã thành công, đang xử lý hay bị chặn.
- Có cần tiếp tục kiểm tra hay không.

Không được dùng `SUCCESS` nếu chưa kiểm tra kết quả thực tế.

## 9. MỤC TIÊU
Tiểu Vũ hiện đã có những phần đang hoạt động ổn định. Mục tiêu là **mở rộng khả năng mà không phá nền**.

Nguyên tắc ưu tiên:

> KEEP THE CORE STABLE. ADD AROUND IT.
