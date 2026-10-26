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

## v0.3.0 — chi tiết ứng dụng / người dùng / thanh toán

- Bỏ Điểm cần kiểm tra.
- Bảng ngày × gói × ứng dụng: người dùng duy nhất, lượt mở, tổng phút,
  phút trung bình của phiên đủ mốc trong ngày, số phiên thiếu stop.
- Bảng người dùng × ngày × gói × ứng dụng để xem từng tài khoản đã dùng gì.
- Thêm nhóm Free / VIP (đúng chữ hoa) bên cạnh warden_free / warden_vip.
- Thanh toán thử nghiệm: đơn tạo / xác nhận theo ngày, theo gói mua, danh sách
  đơn, số đơn hiện còn chờ, tỷ lệ xác nhận của cohort đơn tạo trong khoảng ngày.
  Đơn xác nhận trong kỳ có thể được tạo trước kỳ; tỷ lệ cohort chỉ tính xác nhận
  trước cuối kỳ. Trạng thái chờ là hiện tại, không phải ảnh chụp cuối kỳ.
- Chỉ sử dụng đơn is_test=1. Không ghi / sửa DB billing. Không dùng giá gói hiện
  tại để suy ra tiền đã thanh toán trong quá khứ. Doanh thu thực chưa kết nối.
- Bộ lọc ngày và loại admin áp dụng thanh toán; lọc gói sử dụng / ứng dụng
  không áp dụng vì chưa có quan hệ giao dịch–phiên. Gói mua được phân tích riêng.

Cập nhật bằng lệnh cài như trên. 12 kiểm thử backend và tính toán cục bộ đã qua;
chưa kiểm chứng đăng nhập / hiển thị trên máy chủ thực.

## v0.4.0 — thời gian trong ngày

Chọn một ngày trong khoảng đang lọc tại mục Thời gian trong ngày, nhập tên người
 dùng nếu cần. Bảng hiển thị từng phiên: người dùng, gói lúc mở, ứng dụng, mã
 phiên, ngày giờ mở / đóng, số phút thuộc ngày đã chọn và dòng thời gian 00–24h.
Biểu đồ 24 cột cộng phút phiên theo giờ, phân màu Free/VIP/chưa xác định.
Tổng có thể hơn 60 phút mỗi giờ nếu nhiều người hoặc ứng dụng chạy đồng thời;
đây không phải số phút duy nhất của một người. Rê chuột lên cột xem số phút và
người dùng duy nhất trong giờ. Thiếu mốc không được ước lượng thời lượng.
Các phiên qua nửa đêm giữ nguyên ngày giờ gốc trong bảng nhưng cắt thời lượng
và thanh thời gian theo ngày đã chọn. Bộ lọc tên chỉ tác động mục trong ngày.

## v0.5.0 — giao diện phục vụ kinh doanh và quản lý

Thiết kế được tổ chức theo mục tiêu người xem, tổng quan trước và chi tiết sau:

1. Tổng quan: KPI có ngữ cảnh kỳ trước, hai biểu đồ xu hướng và so sánh Free/VIP
   (người có phiên, số phiên, giờ, phút/người, số ứng dụng/người).
2. Ứng dụng & người dùng: xếp hạng theo tổng giờ, chi tiết từng người/ngày/gói,
   giờ mở/đóng và timeline. Không khẳng định thời gian chạy là thời gian tương tác.
3. Vận hành: bản đồ nhiệt ngày × giờ, đỉnh số phiên đủ mốc chạy đồng thời,
   khung giờ có nhiều phút phiên nhất và độ đầy đủ mốc. Bấm ô nhiệt để chuyển
   sang xem phiên của ngày đó. Không thay thế giám sát CPU/RAM/sức chứa/SLA.
4. Thanh toán: giữ phân tích demo, cohort đơn tạo / ngày xác nhận, không lấy
   đơn thử làm doanh thu; không suy ra chuyển đổi Free→trả phí từ nhóm hiện tại.
5. Nguồn & cách tính: trạng thái kết nối, định nghĩa, câu hỏi quản lý và giới hạn.

Không thêm lại chỉ số giữ chân hoặc panel Điểm cần kiểm tra. Chưa có nguồn tiền
và chi phí thì doanh thu/lợi nhuận hiển thị Chưa kết nối, không hiển thị 0 giả.
Bộ lọc gói/ứng dụng tắt ở mục thanh toán và nguồn để thể hiện phạm vi áp dụng;
bộ lọc ngày và loại admin vẫn áp dụng. Tab điều hướng có thể dùng bàn phím.

Tham khảo thiết kế: Microsoft Power BI dashboard design tips và Tableau dashboard
best practices, truy cập 26/10/2026. Video TikTok được cung cấp không truy cập được
trong phiên nghiên cứu; không coi nội dung video là nguồn đã xác minh.
- https://learn.microsoft.com/en-us/power-bi/create-reports/service-dashboards-design-tips
- https://help.tableau.com/current/pro/desktop/en-us/dashboards_best_practices.htm

Kiểm thử mới: `node --test test_analytics.cjs`, `node test_ui.cjs` (DOM mô phỏng,
không phải kiểm thử hiển thị bằng trình duyệt). Chưa cài trên máy chủ người dùng.


## v0.6.0 — Dashboard Analytics

Dashboard tập trung vào 4 mục: Tổng quan, Ứng dụng, Người dùng và Thanh toán.

- Bỏ lời giới thiệu, dòng trạng thái node/số sự kiện/số lỗi, tab Nguồn & cách tính,
  các ô doanh thu/chi phí/chuyển đổi chưa kết nối và bộ lọc tên tài khoản.
- Tên Dashboard Analytics, liên kết Về Trang chủ; tự loại admin, không có checkbox.
  Tài khoản quản trị hiện tại và dấu admin trong audit đều bị loại khỏi phân tích.
- Tổng quan: người sử dụng duy nhất cả kỳ, Free, VIP, giờ sử dụng, so sánh kỳ trước;
  biểu đồ ngày; top khung giờ theo người duy nhất; ứng dụng hàng đầu; heatmap.
  Một người đổi gói có thể nằm trong cả hai nhóm, không cộng hai nhóm thành tổng.
- Ứng dụng: tổng giờ từng ứng dụng có phân màu và cột Free/VIP/chưa xác định,
  số người, tỷ trọng thời lượng, chi tiết ngày. Tab này luôn hiển thị cả hai gói
  nên bộ lọc nhóm bị tắt; bộ lọc ngày và ứng dụng vẫn hoạt động.
- Người dùng: bảng Free và VIP trong kỳ, ngày sử dụng, tên ứng dụng, giờ/người;
  chọn ngày xem số người và ứng dụng theo từng giờ, thời điểm mở/đóng và timeline.
  Không hiển thị ID phiên, ID đơn hay chỉ số “phiên đủ mốc”. Nội bộ vẫn chỉ tính
  thời lượng có mở và đóng để không suy đoán thời gian khi thiếu nhật ký.
- Hạn mức VIP: đọc trực tiếp user_manager.get_effective_settings và
  quota.used_hours của Sealskin. Hiện người VIP hiện tại, giờ quy đổi đã dùng,
  hạn mức tháng, còn lại, %, cảnh báo gần hết (>=80%) / hết; giới hạn 0 hợp lệ.
  Chu kỳ là tháng UTC hiện tại, bao gồm mọi pool/node mà bộ đếm Sealskin đọc được,
  hệ số pool, thời gian trước khi đổi gói và phiên đang chạy đã tick. Không phụ
  thuộc ngày/gói/ứng dụng đang lọc. Hạn mức tuần/ngày được ghi rõ, không đổi thành
  tháng; không giới hạn hoặc không đọc được không bị hiển thị thành 0 giờ.
- Thanh toán: giữ dữ liệu thử nghiệm đúng nguồn, đơn tạo/xác nhận/chờ, tỷ lệ
  hoàn tất, gói mua, bảng theo ngày và giao dịch; không suy ra doanh thu từ demo.
- Tổng giờ audit vẫn là thời gian mở ứng dụng, gồm thời gian chờ; khác giờ quy
  đổi dùng để trừ hạn mức. Dữ liệu cũ không có gói vẫn giữ Chưa xác định.

Cài đặt và rollback dùng lệnh như trên. Bộ cài tự tìm thư mục app Python, không
cần sửa UI_PATH hay chép vào thư mục ui. Chưa cài trực tiếp trên máy chủ người dùng.


## v0.7.0 — rút gọn theo quyết định quản lý

- Đổi tên biểu đồ: Số lượng người dùng theo ngày, giữ Free/VIP/chưa xác định.
- Bỏ biểu đồ thời gian theo ngày, heatmap ngày–giờ, bảng hiệu quả ứng dụng,
  bảng chi tiết ứng dụng từng ngày và bảng người dùng × ngày × ứng dụng.
- Giữ tổng giờ mỗi ứng dụng phân Free/VIP, bảng người dùng từng nhóm, giờ mở/đóng
  trong ngày và bảng số người/ứng dụng/thời lượng theo giờ.
- Bổ sung 3 chỉ số ngắn gọn: phút sử dụng/người duy nhất trong kỳ, số người
  sử dụng trung bình/ngày (bao gồm ngày trống), tỷ trọng giờ VIP trong tổng giờ
  đang lọc (bao gồm nhóm chưa xác định). Không suy ra doanh thu hay chuyển đổi.
- Bảng VIP sắp theo mức tiêu thụ hạn mức giảm dần; có nút lọc chỉ VIP gần hết
  (>=80%) hoặc hết hạn mức tháng. Hạn mức 0 vẫn được xem là đã hết.
- Đổi 2 KPI thanh toán thành Số lượng đơn VIP tạo trong kỳ và Số lượng đơn VIP
  đã xác nhận trong kỳ; giữ phân biệt ngày tạo/ngày xác nhận, không gộp hai chỉ số.
  Module thanh toán hiện chỉ bán các gói VIP thử nghiệm demo_5m/vip_30d.
- Không đổi backend, quyền truy cập, dữ liệu hoặc cơ chế tính hạn mức.

Kiểm tra: Node test tính toán, DOM mô phỏng và Python test backend. Chưa kiểm tra
trực quan bằng trình duyệt hoặc cài trực tiếp trên máy chủ người dùng.


## v0.8.0 — biểu đồ đa dạng theo mục tiêu phân tích

- Cột nhóm: số người Free/VIP/chưa xác định theo ngày (không xếp chồng người
  vì một tài khoản có thể đổi gói trong ngày); trục số người có vạch nguyên.
- Thanh ngang xếp chồng: tổng thời lượng từng ứng dụng, phân Free/VIP.
- Doughnut: tỷ trọng giờ theo ứng dụng, tối đa 4 ứng dụng và nhóm còn lại.
  Legend giữ số giờ và phần trăm; dữ liệu trống không tạo tỷ trọng giả.
- Thanh ngang: top 5 ứng dụng theo lượt mở trong khoảng đã chọn, độc lập
  với tổng thời lượng để phân biệt mức phổ biến và số giờ tiêu thụ.
- Vùng bậc xếp chồng: phút sử dụng theo 24 giờ trong ngày chọn; mỗi bậc giữ
  đúng một giờ, không nội suy thành hoạt động liên tục giữa các giờ.
- Cột nhóm thanh toán: số đơn VIP tạo / xác nhận mỗi ngày, có thể thuộc các
  đơn khác nhau nên không vẽ thành phễu chuyển đổi.
- Thanh tỷ trọng 100%: trạng thái hiện tại của cùng nhóm đơn VIP tạo trong kỳ,
  bao gồm mọi trạng thái (đã xác nhận, chờ, hủy, khác); nhãn rõ khác với tỷ lệ
  xác nhận trước cuối kỳ đang hiển thị trên KPI.
- Giữ thanh tiến độ hạn mức VIP và dòng thời gian mở/đóng người dùng.
- Không thêm lại các phần đã bỏ ở v0.7.0; không sửa backend hoặc dữ liệu.

SVG nội bộ cùng origin, không dùng CDN và không gửi dữ liệu cho bên thứ ba.
Đã kiểm tra ba ảnh người dùng gửi (tỷ trọng thời lượng / xếp hạng / vùng).
Link TikTok 7660519530476752148 vẫn không truy cập được ngày 26/10/2026,
không khẳng định thiết kế đã đối chiếu với nội dung video.
Tham khảo cách chọn biểu đồ: Microsoft Learn visualization types và
Datawrapper chart types guide (26/10/2026).
- https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-types-for-reports-and-q-and-a
- https://www.datawrapper.de/blog/chart-types-guide

Kiểm thử tính toán, SVG và DOM mô phỏng; chưa kiểm thử trực quan bằng trình duyệt
hoặc trên máy chủ người dùng.
