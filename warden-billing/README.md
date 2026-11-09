# Warden Billing mô phỏng — v1

Module chạy trong Sealskin trên một node và dùng danh tính từ phiên đăng nhập. Khi người dùng bấm Nâng cấp, hệ thống tự xác nhận đơn mô phỏng, cấp VIP và thu hồi khi hết hạn. Không kết nối ngân hàng, không xử lý tiền thật.

## Chuẩn bị

Trong giao diện quản trị Sealskin tạo hai nhóm `warden_free`, `warden_vip`, thiết lập ứng dụng và hạn mức tương ứng. Tắt Administrator trên cả hai nhóm. Không ánh xạ Free/VIP qua nhóm IdP: nhóm do IdP gán không thể bị module thu hồi bằng cách sửa membership cục bộ.

Dùng một tài khoản người dùng bình thường để demo, đã được duyệt trong Sealskin. Không dùng admin làm người mua. Tài khoản có quyền quản trị không được cấp/hạ gói bởi module.

## Cài trên Ubuntu

Đặt thư mục này tại `/home/ubuntu/warden-billing`, sau đó:

```bash
cd /home/ubuntu/warden-billing
sudo bash install.sh sealskin
```

Bộ cài kiểm tra cấu trúc phiên bản thực tế, kiểm tra nhóm, sao lưu api.py rồi đăng ký module. Việc cài khởi động lại container: lưu và đóng phiên trước.

Nếu đưa cả thư mục vào repository `trinpce192008/analytic`, trên máy chủ đã clone repository đó:

```bash
cd /home/ubuntu/analytic
git pull --ff-only
cd warden-billing
sudo bash install.sh sealskin
```

Những lệnh Git này chỉ áp dụng sau khi bạn đã đưa thư mục lên repository. Bộ cài hiện được cung cấp dưới dạng ZIP, chưa tự đẩy vào repository.

Trên máy đã cài, chế độ `install` giữ các tệp giao diện hiện tại. Dùng
`sudo bash install.sh sealskin restore-ui` trong thư mục `warden-billing` để
cài lại giao diện thẻ Free, VIP 5 phút và VIP 30 ngày. Chế độ này sao lưu
HTML và JavaScript hiện tại trong `/config/warden-billing/backups/restore-ui-*`.

## Mở trang

Đăng nhập Sealskin, mở trên cùng origin:

```text
/api/warden-billing
```

Địa chỉ dự kiến sau cài:

```text
https://sealskin.wardenmvp.duckdns.org:8443/api/warden-billing
```

HTML/JS chỉ là vỏ giao diện, không chứa dữ liệu tài khoản. API đọc và ghi đều kiểm tra danh tính phía máy chủ; API admin chỉ nhận tài khoản tích hợp admin. Yêu cầu ghi có header riêng và kiểm tra same-origin. Không cấu hình CORS mở cho module.

Module là trang riêng trên cùng Sealskin, chưa thêm tab vào sidebar gốc. Trang có đường dẫn quay lại Sealskin và Analytics; đường dẫn Analytics chỉ hoạt động nếu dashboard trước đã được cài.

## Trình diễn

1. Cửa sổ người dùng bình thường: mở trang, chọn gói VIP thử nghiệm 5 phút, bấm Nâng cấp thử nghiệm. Danh tính người mua lấy từ phiên đăng nhập.
2. Hệ thống tự xác nhận đơn và đưa tài khoản vào nhóm `warden_vip`. Trang hiển thị trạng thái cấp quyền và ngày hết hạn.
3. Admin có thể mở cùng trang để kiểm tra đơn đã xác nhận. Các đơn cũ còn chờ vẫn có thể được xác nhận thủ công.
4. Sau 5 phút, tác vụ trên máy chủ (15 giây/lần) thay VIP về Free. Tác vụ tiếp tục chạy khi trang đóng.

Có thêm gói VIP 30 ngày, giá mô phỏng 429.000 đ. Gói 5 phút giá 0 đ. Chỉnh cấu hình PLANS trong warden_billing.py trước khi cài nếu cần.

## Quy tắc

- Hệ thống dùng lại đơn thử nghiệm còn chờ nếu trùng gói đã chọn và hủy các đơn thử nghiệm còn chờ khác của tài khoản.
- Bấm lặp khi VIP còn hiệu lực hoặc đang chờ cấp quyền không tạo đơn mới hay gia hạn.
- Hạn mới = max(hiện tại, hạn cũ) + thời hạn gói. Tính hạn được ghi trong transaction SQLite trước khi cấp quyền.
- Đã xác nhận và đã cấp quyền là hai trạng thái riêng. Ghi quyền lỗi giữ pending_grant, worker thử lại mà không cộng thêm hạn.
- Hết hạn chuyển pending_revoke nếu cập nhật lỗi, tiếp tục thử lại.
- Đọc settings đang lưu, thay hai nhóm gói, giữ nhóm và trường khác. Dùng hàm cập nhật gốc của Sealskin trên chính tiến trình máy chủ, để nạp lại dữ liệu; không viết trực tiếp YAML hay cần root key phía trình duyệt.
- Module quản lý membership gói của các tài khoản có subscription. Nếu admin sửa tay nhóm gói, worker có thể đưa về trạng thái subscription đang lưu; gỡ module dừng cơ chế này.
- Không dừng phiên ứng dụng đang mở. Thu hồi nhóm chỉ điều chỉnh quyền; không khẳng định phiên cũ đã kết thúc.
- Không tạo báo cáo doanh thu thật. Giao dịch có is_test=1; thống kê Billing trong trang admin và bảng billing_events. Chưa ghép vào biểu đồ Analytics cũ hoặc Google Sheets.

## Lưu trữ và vận hành

SQLite tại `/config/warden-billing/billing.sqlite3` với quyền 0600. `/config` phải là volume bền vững như triển khai Sealskin hiện tại. Sao lưu cả volume trước khi vận hành. Không upload DB, log hay khóa lên GitHub.

Chỉ dùng trên một node / một tiến trình API cho bản MVP. Không dùng làm billing nhiều node hoặc dịch vụ thanh toán thật. Các cập nhật Sealskin và SQLite không phải một transaction chung; worker đối chiếu lại theo trạng thái mong muốn để khôi phục sau lỗi. Không áp dụng multi-node vì module gọi hàm nội bộ và không phát thông báo thay đổi cluster.

Image recreate có thể làm mất module; restart cùng container vẫn giữ. Lưu bộ cài, cài lại sau khi kiểm tra tương thích. Không mount api.py cũ đè lên image mới.

## Gỡ module

```bash
sudo bash install.sh sealskin rollback
```

Lệnh bỏ riêng đăng ký module, giữ DB và khởi động lại. Quyền VIP hiện tại không tự thu hồi khi gỡ: admin phải rà soát và đổi về Free theo nhu cầu trước/sau khi gỡ. Không xóa dữ liệu người dùng.

## Kiểm tra

Đã chạy 4 nhóm unit test bằng FastAPI TestClient với phần xác thực và user_manager mô phỏng: tạo/xác nhận/thu hồi, giữ thiết lập khác, xác nhận lặp, gia hạn nối hạn cũ, lỗi cấp quyền rồi thử lại không cộng hạn, chặn user thường vào admin và chặn yêu cầu ghi thiếu same-origin/header. Kiểm tra cú pháp Python, JavaScript và Bash đã đạt.

Chưa chạy tích hợp trên container Lightsail 0.4.0-ls64 của bạn; chưa kiểm tra giao diện trực quan bằng trình duyệt. Preflight chỉ kiểm tra cấu trúc, không thay thế kiểm thử tích hợp. Nếu lỗi, gửi thông báo đã loại bỏ thông tin nhạy cảm; không gửi root key.

Tham chiếu mã gốc: https://github.com/selkies-project/sealskin — cơ chế update_user_settings và mô hình UpdateUserRequest đã được người dùng xác minh từ máy chủ trong cuộc trò chuyện.
