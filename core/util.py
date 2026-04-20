import json
import os
import sys
import time

def get_base_path():
    """Returns the base path for static files, handling PyInstaller environment."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")

def format_uptime(seconds):
    """Formats seconds into h m s format."""
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    s = s % 60
    return f"{h}h {m}m {s}s"

def load_config(file_name="config.json"):
    """Loads configuration settings."""
    base = get_base_path()
    file_path = os.path.join(base, file_name)
    
    if not os.path.exists(file_path):
        return {
            "start_port": 1112,
            "rotation_interval": 300,
            "rotation_enabled": True,
            "use_key_proxy": True,
            "token_proxy_port": 9898
        }
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            return {
                "start_port": config.get("start_port", 1112),
                "rotation_interval": config.get("rotation_interval", 300),
                "rotation_enabled": config.get("rotation_enabled", True),
                "use_key_proxy": config.get("use_key_proxy", True),
                "token_proxy_port": config.get("token_proxy_port", 9898)
            }
    except Exception:
        return {"start_port": 1112}

def load_proxies(file_name="proxies.txt"):
    """Loads static proxies from file."""
    file_path = os.path.join(get_base_path(), file_name)
    proxies = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        proxies.append({"type": "static", "raw": line})
        except: pass
    return proxies

def load_keys(file_name="key.txt"):
    """Loads rotation keys from file."""
    file_path = os.path.join(get_base_path(), file_name)
    keys = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        keys.append({"type": "api", "raw": line})
        except: pass
    return keys

def clear_port(port):
    import subprocess
    try:
        # Silently attempt to clear port
        cmd = f"Stop-Process -Id (Get-NetTCPConnection -LocalPort {port}).OwningProcess -Force"
        subprocess.run(["powershell", "-Command", cmd], capture_output=True)
    except:
        pass
