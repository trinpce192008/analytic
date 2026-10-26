# Warden Analytics dành cho Sealskin — v1

Dashboard chạy bên trong tiến trình FastAPI của container Sealskin, cùng origin HTTPS và dùng phiên đăng nhập Sealskin. Không tạo dịch vụ công khai riêng, không yêu cầu nhập root key vào dashboard. Chỉ tài khoản tích hợp `admin` được truy cập; quản trị viên khác cũng bị từ chối.

## Cài đặt

1. Giải nén và chép thư mục `warden-analytics-sealskin` lên `/home/ubuntu/` bằng công cụ truyền tệp SSH/SFTP bạn đang sử dụng.
2. Đăng nhập SSH vào máy Ubuntu, chạy:

```bash
cd /home/ubuntu/warden-analytics-sealskin
sudo bash install.sh sealskin
```

Script kiểm tra cấu trúc mã đang cài, sao lưu api.py trong `/config/warden-analytics/backups`, thêm router rồi khởi động lại container. Hãy thực hiện khi không có phiên làm việc quan trọng vì việc khởi động lại có thể ngắt phiên.

3. Đăng nhập Sealskin như thường lệ bằng tài khoản admin/root key. Mở cùng origin, thêm đường dẫn:

```text
/api/warden-analytics
```

Với địa chỉ hiện tại của Warden, URL sau khi cài là:

```text
https://sealskin.wardenmvp.duckdns.org:8443/api/warden-analytics
```

Đây là URL dự kiến sau cài, chưa được xác minh trên máy chủ của bạn. Bản v1 là trang bổ sung trong Sealskin, chưa chèn một tab vào sidebar gốc. Có thể đánh dấu trang trong trình duyệt để truy cập nhanh.

## Dữ liệu

- Đọc `<settings.node_state_path>/audit/YYYY-MM-DD.log` trên node hiện tại; không cần đoán host mount.
- Giữ UTC trong nguồn và xuất CSV; hiển thị theo Asia/Ho_Chi_Minh.
- Chỉ số: tài khoản có hoạt động, sự kiện sign_in, lượt launch và thời lượng trung bình của phiên có đủ launch/stop.
- Ghép phiên trước khi lọc ngày, hỗ trợ qua ngày. Khoảng lọc phiên áp dụng theo ngày mở, hoặc ngày đóng nếu thiếu mở.
- Thiếu stop được ghi “Thiếu sự kiện dừng”, không khẳng định còn đang chạy.
- Mặc định loại `user=admin` và sự kiện có `admin=true`. Với tài khoản quản trị khác chỉ được đánh dấu ở sự kiện sign_in, log không đủ thông tin để nhận diện toàn bộ hoạt động quản trị của người đó.
- Bộ lọc ngày, tìm kiếm, phân trang 12 phiên, xuất CSV các phiên đang lọc.
- Làm mới mỗi 60 giây khi trang đang mở; không phải tác vụ đồng bộ nền.
- Biểu đồ tối đa 31 ngày có phát sinh launch; không đại diện cho 31 ngày liên tục.
- Giới hạn đọc 32 MiB mỗi lần; cảnh báo khi dữ liệu bị giới hạn. Bản v1 phù hợp dữ liệu MVP; lịch sử lớn cần tổng hợp qua cơ sở dữ liệu.
- Website và thanh toán: “Chưa kết nối”, không tạo doanh thu giả.
- Không gửi dữ liệu tới Google Sheets hay bên thứ ba.

## Hoàn tác

```bash
cd /home/ubuntu/warden-analytics-sealskin
sudo bash install.sh sealskin rollback
```

Lệnh bỏ riêng khối đăng ký router Warden rồi khởi động lại container. Không khôi phục toàn bộ api.py đè lên những thay đổi không liên quan.

## Cập nhật container

Bản v1 sửa lớp ghi của container đang chạy. Khi recreate/pull image mới, phần này có thể mất; giữ bộ cài và chạy lại sau khi kiểm tra tương thích. Khởi động lại cùng container không làm mất. Không tự động mount đè api.py của bản cũ vào image mới. Bản build tùy chỉnh cố định phiên bản là bước triển khai lâu dài tiếp theo.

## Kiểm tra đã thực hiện

- Python unit tests: chặn không đăng nhập, user thường và admin khác; cho admin vào; kiểm tra no-store, dòng log lỗi, chống dòng trùng, đọc qua hai ngày và cảnh báo giới hạn.
- Test auth sử dụng dependency Sealskin mô phỏng; chưa xác minh cookie và tích hợp trên server đang chạy của bạn.
- Node kiểm tra cú pháp JavaScript; bash kiểm tra cú pháp bộ cài.
- Kiểm tra giao diện desktop bằng trình duyệt với dữ liệu trống và dữ liệu thử; chưa kiểm tra trực quan tablet/mobile.

Nếu preflight báo “Unsupported”, dừng tại đó và gửi thông báo lỗi để điều chỉnh theo mã thực tế; không tự bỏ kiểm tra. Không gửi root key hoặc toàn bộ cấu hình.

## Tham khảo cơ chế tích hợp

Đã kiểm tra mã upstream `selkies-project/sealskin` ở `server/app/api.py`, `server/app/security.py`, `server/app/routers/ui.py` và `server/app/audit.py` ngày 26/10/2026. Mã mới dùng dependency `verify_admin` và `settings.node_state_path` từ phiên bản trên máy người dùng. Chưa xác minh đầy đủ trên `0.4.0-ls64`; bộ cài kiểm tra cấu trúc trước khi thay đổi.

- https://github.com/selkies-project/sealskin
- https://docs.sealskin.app/latest/api

## Warden Analytics v0.2.0 — phân tích nhiều ngày

Bản này cập nhật dashboard trong Sealskin; không thay thế phần mềm Windows
Warden Desktop v0.1.3. Không có biểu đồ giữ chân D1/D7/D30.

Cập nhật trên host đã clone repository:

```bash
cd /home/ubuntu/analytic
git pull --ff-only
sudo bash install.sh sealskin
```

Docker sẽ khởi động lại; thực hiện lúc không có phiên làm việc quan trọng.
Đăng nhập Sealskin bằng tài khoản admin tích hợp, mở:
https://sealskin.wardenmvp.duckdns.org:8443/api/warden-analytics

### Có gì mới

- Chọn 7/30/90 ngày hoặc tùy chọn tối đa 366 ngày.
- Biểu đồ theo ngày: người dùng Free/VIP/chưa xác định và giờ chạy phiên.
- Bộ lọc ứng dụng, gói lúc mở phiên; mặc định loại tài khoản admin.
- Người dùng duy nhất trong kỳ, phiên mở, tổng giờ, thời lượng trung bình;
  so với khoảng liền trước có cùng số ngày. Số 0 không chứng minh thu thập đủ.
- Chia thời lượng phiên qua ngày theo múi giờ Việt Nam, cắt ở biên bộ lọc;
  không ước lượng thời lượng cho phiên thiếu stop. Một người có thể xuất hiện
  ở cả Free và VIP trong ngày nếu mở phiên trước và sau khi nâng cấp.
- Ghi trường plan vào sự kiện launch mới qua audit hook (nhóm warden_free /
  warden_vip). Phiên cũ không có plan hiện Chưa xác định, không phân loại ngược.
  Gói là nhóm tại lúc mở phiên, không tách giữa phiên nếu gói thay đổi.
- Chỉ đọc cơ sở dữ liệu billing thử nghiệm sẵn có; không tạo đơn và không
  tính giao dịch is_test vào doanh thu. Website/GA4 và tiền thực chưa kết nối.
- CSV chi tiết ngày theo các bộ lọc đang chọn. Tự đọc lại mỗi 60 giây khi trang mở.
- Không theo dõi nội dung trong ứng dụng, URL duyệt web, bàn phím, mật khẩu.
  Audit mở/đóng không đo được thời gian tương tác hay hành trình tính năng web.

### Giới hạn và khôi phục

Chỉ dữ liệu node hiện tại, tối đa 32 MiB nhật ký gần nhất, cảnh báo khi cắt.
Phiên bị cắt mất launch/stop sẽ không được tính thời lượng. Nhóm khác hai nhóm
chuẩn hiện Chưa xác định. Nên kiểm tra một phiên mới để xác nhận hook ghi plan
trên phiên bản Sealskin thực tế. Installer sửa module trong container; khi
recreate/update image cần cài lại. Không đổi chính sách đăng nhập hay phân quyền.

```bash
sudo bash install.sh sealskin rollback
```

Rollback gỡ route dashboard và restart container, loại bỏ hook trong tiến trình;
không xóa nhật ký, không xóa dữ liệu billing. Kiểm thử cục bộ với xác thực mô phỏng:
`python3 -m unittest discover -s . -p test_dashboard.py -v` và
`node --test test_analytics.cjs`. Chưa kiểm chứng trên máy chủ người dùng.
