# Solumate Project

## Language / Ngôn ngữ
- Tiếng Việt
- English

This repository provides Vietnamese and English guides for beginners.

## Đóng góp / Donation
Nếu bạn thấy dự án hữu ích và muốn ủng hộ tác giả duy trì/hoàn thiện dự án, bạn có thể donation theo thông tin dưới đây:

- MoMo: 0799640848
- VietinBank: 0799640848 - Đoàn Thanh Lực

Xin cảm ơn bạn đã ủng hộ.

## Donation
If you find this project useful and would like to support continued development/maintenance:

- MoMo: 0799640848
- VietinBank: 0799640848 - Đoàn Thanh Lực

Thank you for your support.

---

# Proxy IPv6 Manager

Một REST API viết bằng **FastAPI** cho phép:

- Tạo và quản lý proxy dựa trên địa chỉ IPv6.
- Tự động gán địa chỉ IPv6 vào card mạng (interface).
- Quản lý vòng đời proxy: **run, stop, rotate, delete**.
- Liệt kê card mạng và lấy IPv4/IPv6 đang cấu hình.
- Hỗ trợ realtime bằng WebSocket để cập nhật trạng thái.

---

## Chạy 1 file Python tự động (khuyên dùng)

Cách này dùng được cho **Windows hoặc Linux**. Script `run_proxyv6.py` sẽ tự động:

- nhận diện hệ điều hành Windows/Linux,
- tạo `venv` nếu chưa có,
- cài/cập nhật `pip` và thư viện trong `requirements.txt`,
- tự chọn card mạng mặc định,
- mở web UI tại `http://127.0.0.1:9002`,
- tự tạo và chạy **3 proxy IPv6** mặc định, bắt đầu từ port `10000`.

### Windows

Mở **PowerShell bằng Run as administrator**, vào thư mục project rồi chạy:

```powershell
python run_proxyv6.py
```

Hoặc bấm chuột phải `run_windows.bat` -> **Run as administrator**.

### Linux

Chạy bằng root/sudo để tool có quyền gán/xóa IPv6 trên card mạng:

```bash
sudo python3 run_proxyv6.py
```

### Tuỳ chọn nhanh

Tạo đúng 3 proxy trên card tự nhận:

```bash
python run_proxyv6.py --count 3
```

Chỉ cài thư viện, mở UI, không tự tạo proxy:

```bash
python run_proxyv6.py --no-auto-create
```

Chỉ định card mạng và group:

```bash
python run_proxyv6.py --interface Ethernet --group group-main --count 3
```

Trong UI, ô **Số proxy** cho phép tạo nhiều proxy một lần; nút **Xoay** trong bảng hoặc **Xoay theo port** sẽ remove IPv6 cũ, add IPv6 mới và chạy lại proxy giữ nguyên port.

---

## Chạy nhanh trên Windows (dễ nhất)

Nếu bạn dùng Windows và chưa quen lệnh `pip`, hãy làm theo cách này:

### Cách 1: Chạy tự động bằng file `.bat`

1. Cài **Python 3.9+** từ trang Python chính thức.
2. Khi cài Python, nhớ tick **Add python.exe to PATH**.
3. Tải/mở thư mục source code này.
4. Bấm chuột phải vào `run_windows.bat` -> chọn **Run as administrator**.
5. File `.bat` sẽ tự động:
   - kiểm tra Python,
   - tạo thư mục `venv`,
   - cài/cập nhật `pip`,
   - cài thư viện trong `requirements.txt`,
   - mở web tại `http://127.0.0.1:9002`.

Nếu chỉ xem giao diện hoặc API không cần thêm/xóa IPv6, bạn có thể chạy bình thường. Nếu muốn tạo/xóa IPv6 trên card mạng, nên chạy bằng **Run as administrator**.

### Cách 2: Chạy thủ công bằng PowerShell

Mở **PowerShell** trong thư mục project, sau đó chạy từng lệnh:

```powershell
python --version
python -m ensurepip --upgrade
python -m pip install --upgrade pip
python -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
python server.py
```

Sau khi server chạy, mở trình duyệt:

```text
http://127.0.0.1:9002
```

Nếu Windows báo không nhận lệnh `python`, hãy thử:

```powershell
py -3 --version
py -3 -m pip install --upgrade pip
py -3 -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
python server.py
```

### Lỗi thường gặp trên Windows

- **Không có pip**: chạy `python -m ensurepip --upgrade`, sau đó chạy lại `python -m pip install --upgrade pip`.
- **Không nhận lệnh python**: cài lại Python và tick **Add python.exe to PATH**, hoặc dùng lệnh `py -3`.
- **Không tạo/xóa được IPv6**: tắt server, mở lại PowerShell hoặc `run_windows.bat` bằng **Run as administrator**.
- **Không vào được web từ máy khác trong LAN**: kiểm tra firewall Windows và mở port `9002` nếu cần.

---

## Yêu cầu hệ thống

- Python 3.9+
- Windows hoặc Linux
- Quyền Administrator trên Windows hoặc quyền root/sudo trên Linux để thêm/xóa IPv6
- Linux cần gói `iproute2` để dùng lệnh `ip`
- Các thư viện Python (xem `requirements.txt`)

Cài đặt trên Windows:

```powershell
python -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
```

Cài đặt trên Linux:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

---

## Cấu trúc thư mục

```text
project/
|-- run_proxyv6.py        # Chạy 1 file: tạo venv, cài libs, mở UI, auto tạo 3 proxy
|-- run_windows.bat       # Chạy nhanh trên Windows: gọi run_proxyv6.py
|-- server.py              # FastAPI server (API endpoints + websocket)
|-- client.html            # UI dashboard
|-- client.js              # UI logic + realtime socket
|-- utils/
|   |-- generate_ipv6.py   # Tạo/xóa/gán IPv6 vào card mạng
|   |-- db.py              # Quản lý SQLite database
|   |-- proxy.py           # Logic chạy/stop proxy TCP
|-- data/
|   |-- ipv6_address.db    # SQLite database lưu proxy
|-- requirements.txt
|-- LICENSE
```

---

## Chạy server

Windows (mở PowerShell bằng Run as Administrator nếu cần tạo/xóa IPv6):

```powershell
python server.py
```

Linux (chạy root/sudo nếu cần tạo/xóa IPv6):

```bash
sudo venv/bin/python server.py
```

hoặc tự chọn host/port:

```bash
PROXYV6_HOST=0.0.0.0 PROXYV6_PORT=9002 uvicorn server:app --host 0.0.0.0 --port 9002
```

- Web UI local: `http://127.0.0.1:9002`
- Web UI từ máy khác trong LAN: `http://<IP-may-chu>:9002`
- API base: tự nhận theo host đang mở Web UI, hoặc nhập thủ công trong ô API Base URL
- WebSocket realtime: `ws://<host>:9002/ws/events`

---

## API Endpoints

### Proxy Management

- `POST /proxy/create` -> Tạo mới 1 hoặc nhiều proxy với IPv6 random (`count` mặc định là 1)
- `POST /proxy/run_all` -> Chạy toàn bộ proxy trong DB
- `POST /proxy/run_by_ids` -> Chạy proxy theo danh sách id
- `POST /proxy/stop_by_ids` -> Dừng proxy theo danh sách id
- `POST /proxy/stop/{port}` -> Dừng proxy theo port
- `POST /proxy/rotate/{port}` -> Xoay IP (remove IPv6 cũ, add IPv6 mới, giữ nguyên port)
- `DELETE /proxy/{id}` -> Xóa proxy (nếu không đang chạy)
- `GET /proxy` -> Liệt kê toàn bộ proxy với trạng thái running/stopped

### Network

- `GET /network/adapters` -> Lấy danh sách card mạng và IPv4
- `GET /network/adapters/{card_name}/ipv6` -> Lấy IPv6 của card mạng chỉ định
- `DELETE /network/adapters/{card_name}/ipv6/{ipv6_address}` -> Xóa 1 IPv6 cụ thể khỏi card mạng

### Realtime

- `WS /ws/events`
- Server phát các event `operation` và `proxy_snapshot` để cập nhật UI theo thời gian thực.

---

## Ví dụ cURL

### Tạo proxy mới

```bash
curl --location 'http://127.0.0.1:9002/proxy/create' \
--header 'Content-Type: application/json' \
--data '{
  "group_name": "group1",
  "interface_name": "Ethernet",
  "count": 3
}'
```

### Xem danh sách proxy

```bash
curl -X GET "http://127.0.0.1:9002/proxy"
```

### Chạy tất cả proxy

```bash
curl --location --request POST 'http://127.0.0.1:9002/proxy/run_all'
```

### Chạy theo IDs

```bash
curl --location --request POST 'http://127.0.0.1:9002/proxy/run_by_ids' \
--header 'Content-Type: application/json' \
--data '[1,2,3]'
```

### Dừng theo IDs

```bash
curl --location --request POST 'http://127.0.0.1:9002/proxy/stop_by_ids' \
--header 'Content-Type: application/json' \
--data '[1,2,3]'
```

### Dừng theo port

```bash
curl --location --request POST 'http://127.0.0.1:9002/proxy/stop/10000'
```

### Xoay IPv6 theo port

```bash
curl --location --request POST 'http://127.0.0.1:9002/proxy/rotate/10005'
```

### Xóa proxy

```bash
curl --location --request DELETE 'http://127.0.0.1:9002/proxy/4'
```

### Danh sách card mạng

```bash
curl --location 'http://127.0.0.1:9002/network/adapters'
```

### Danh sách IPv6 theo card

```bash
curl --location 'http://127.0.0.1:9002/network/adapters/Ethernet/ipv6'
```

### Xóa trực tiếp 1 IPv6 trong máy

```bash
curl --location --request DELETE 'http://127.0.0.1:9002/network/adapters/Ethernet/ipv6/2402:800:6344:86b:57d6:4ead:8312:9703'
```

---

## Lưu ý

- Windows cần chạy bằng **Administrator** để thêm hoặc xóa IPv6 vào interface.
- Linux cần chạy bằng **root/sudo** và cần lệnh `ip` (`iproute2`) để thêm/xóa IPv6 vào interface.
- Trên Linux, tên interface thường là `eth0`, `ens18`, `enp0s3`, ... thay vì `Ethernet`.
- Nếu máy không có kết nối IPv6 public, proxy có thể không hoạt động đúng.
- Database SQLite lưu trong thư mục `data/ipv6_address.db`.

---

## Build (tùy chọn)

```bash
python setup.py build_ext
```

```bash
pyinstaller --onefile --name server2 --icon=solumate_icon.ico --add-data "utils_ext;utils_ext" .\server.py
```
