from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import os
import time

def run_selenium_proxy():
    # 1. Đường dẫn lưu trữ dữ liệu (Profile)
    # Chúng ta sẽ lưu vào thư mục 'data' nằm ngay tại thư mục dự án
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data", "profile_5555")
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"[*] Created new profile directory: {data_dir}")

    # 2. Cấu hình Chrome Options
    chrome_options = Options()
    
    # Thiết lập PROXY (Kết nối tới cổng 5555 của VuaProxy)
    proxy_server = "127.0.0.1:5555"
    chrome_options.add_argument(f'--proxy-server={proxy_server}')
    
    # Thiết lập thư mục lưu trữ DATA
    chrome_options.add_argument(f'--user-data-dir={data_dir}')
    
    # Các tùy chọn tối ưu khác (Ẩn log, tránh bị phát hiện...)
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    print(f"[*] Launching Chrome via VuaProxy @ {proxy_server}...")
    
    try:
        # Khởi tạo trình duyệt
        # Selenium 4.x sẽ tự động tải Driver nếu bạn chưa có
        driver = webdriver.Chrome(options=chrome_options)
        
        # 3. Truy cập trang kiểm tra IP
        target_url = "http://api.ipify.org?format=json"
        driver.get(target_url)
        
        print(f"[*] Successfully navigated to: {target_url}")
        
        # Đợi 10 giây để bạn quan sát kết quả trên màn hình
        time.sleep(10)
        
        # Lấy nội dung JSON hiện lên màn hình
        content = driver.find_element("tag name", "pre").text
        print(f"[+] Result from Screen: {content}")
        
    except Exception as e:
        print(f"[red][!] Selenium Error: {e}[/]")
    finally:
        if 'driver' in locals():
            driver.quit()
            print("[*] Browser closed.")

if __name__ == "__main__":
    run_selenium_proxy()
