import json
import os
import sys
import time

def get_paths_to_check():
    """Returns a list of potential directories where config files might exist."""
    paths = []
    # 1. Current Working Directory (where the user is in CMD)
    paths.append(os.path.abspath("."))
    # 2. Directory where the .exe or script is located
    if hasattr(sys, '_MEIPASS'):
        paths.append(os.path.dirname(sys.executable))
    else:
        paths.append(os.path.dirname(os.path.abspath(__file__)))
        paths.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    return list(dict.fromkeys(paths)) # Remove duplicates

def find_file(file_name):
    """Robustly searches for a file in multiple potential locations."""
    for path in get_paths_to_check():
        target = os.path.join(path, file_name)
        if os.path.exists(target):
            return target
    return None

def format_uptime(seconds):
    """Formats seconds into h m s format."""
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    s = s % 60
    return f"{h}h {m}m {s}s"

def load_config(file_name="config.json"):
    """Loads configuration settings with redundant path checking."""
    file_path = find_file(file_name)
    
    defaults = {
        "start_port": 1112,
        "rotation_enabled": True,
        "rotation_interval": 300,
        "use_key_proxy": True
    }
    
    if not file_path:
        # Last resort: Try to create it in the SAME folder as the EXE
        exe_dir = os.path.dirname(sys.executable) if hasattr(sys, '_MEIPASS') else os.path.abspath(".")
        new_path = os.path.join(exe_dir, file_name)
        try:
            if not os.path.exists(new_path):
                with open(new_path, "w", encoding="utf-8") as f:
                    json.dump(defaults, f, indent=2)
        except: pass
        return defaults
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            return {
                "start_port": config.get("start_port", 1112),
                "rotation_enabled": config.get("rotation_enabled", True),
                "rotation_interval": config.get("rotation_interval", 300),
                "use_key_proxy": config.get("use_key_proxy", True)
            }
    except Exception:
        return defaults

def load_proxies(file_name="proxies.txt"):
    """Loads static proxies using redundant path checking."""
    file_path = find_file(file_name)
    proxies = []
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        proxies.append({"type": "static", "raw": line})
        except: pass
    return proxies

def load_keys(file_name="key.txt"):
    """Loads rotation keys using redundant path checking."""
    file_path = find_file(file_name)
    keys = []
    if file_path:
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
        cmd = f"Stop-Process -Id (Get-NetTCPConnection -LocalPort {port}).OwningProcess -Force"
        subprocess.run(["powershell", "-Command", cmd], capture_output=True)
    except: pass
