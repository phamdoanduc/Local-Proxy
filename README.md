# VuaProxy - Local Proxy Engine (v4.0)

![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**VuaProxy - Local Proxy Engine** là một giải pháp Proxy Gateway hiệu năng cao, giúp chuyển đổi các hệ thống Proxy có xác thực (User/Pass) hoặc các Key xoay IP thành các cổng Local Proxy không xác thực. Công cụ được thiết kế dành riêng cho các tác vụ Automation và MMO quy mô lớn.

## 🛒 Mua Proxy Ở Đâu?

Để có trải nghiệm tốt nhất và được hỗ trợ tối ưu với bộ công cụ này, bạn có thể mua các loại Proxy xoay IP, Proxy dân cư chất lượng cao tại:
👉 **[VuaProxy.com](https://vuaproxy.com)** - Hệ thống cung cấp Proxy hàng đầu Việt Nam.

## ✨ Tính năng nổi bật

- **Kiến trúc Modular**: Dễ dàng bảo trì và mở rộng.
- **Hỗ trợ Đa nguồn**: Nạp Proxy từ `proxies.txt` (Tĩnh) hoặc `key.txt` (Xoay IP VuaProxy).
- **Tự động Xoay IP**: Tích hợp bộ đếm ngược (Cooldown) đồng bộ trực tiếp với server VuaProxy.
- **Dashboard v4.0**: Giao diện trực quan trên Command Line, theo dõi kết nối và trạng thái IP tức thì.
- **Tối ưu Hiệu năng**: Cơ chế Tunneling bất đồng bộ (Asyncio) cực nhẹ, hỗ trợ hàng trăm cổng đồng thời.

## 🚀 Hướng dẫn cài đặt

1. **Yêu cầu**: Python 3.11 trở lên.
2. **Cài đặt thư viện**:
   ```bash
   pip install aiohttp rich keyboard
   ```
3. **Cấu hình**: Chỉnh sửa file `config.json` để thiết lập cổng và chế độ chạy.

## ⚙️ Cấu hình (config.json)

- `start_port`: Cổng Local bắt đầu.
- `use_key_proxy`: `true` để dùng Key xoay, `false` để dùng Proxy tĩnh.
- `rotation_enabled`: Bật/Tắt tự động xoay IP.

## ⌨️ Phím tắt điều khiển

- **`R`**: Xoay IP thủ công cho tất cả các cổng (Manual Rotate).
- **`Q`**: Thoát chương trình an toàn.

## 🛡️ Bảo mật
Các file cấu hình nhạy cảm (`config.json`, `key.txt`, `proxies.txt`) đã được đưa vào `.gitignore` để tránh bị lộ thông tin khi đẩy lên GitHub.

---
*Phát triển bởi Pham Doan Duc Admin VuaProxy.com & Antigravity AI.* =)))))
