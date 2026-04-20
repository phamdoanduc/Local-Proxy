import json
import os
import sys
import time

def get_paths_to_check():
    """Returns a list of potential directories where config files might exist."""
    paths = []
    # 1. Current Working Directory
    paths.append(os.getcwd())
    # 2. Directory where the .exe or script is located
    if hasattr(sys, '_MEIPASS'):
        paths.append(os.path.dirname(sys.executable))
    else:
        paths.append(os.path.dirname(os.path.abspath(__file__)))
    
    # 3. Handle possible renamed executable path
    try:
        paths.append(os.path.dirname(os.path.realpath(sys.argv[0])))
    except: pass
        
    return list(dict.fromkeys(paths)) # Remove duplicates

def get_diagnostic_info():
    """Returns a string with diagnostic info about search paths."""
    info = "\n--- [DIAGNOSTIC INFO] ---\n"
    info += f"EXE Path: {sys.executable}\n"
    info += f"CWD Path: {os.getcwd()}\n"
    info += "Search Directories:\n"
    for p in get_paths_to_check():
        info += f"  > {p}\n"
    
    files = ["config.json", "proxies.txt", "key.txt"]
    info += "File Status:\n"
    for f in files:
        path = find_file(f)
        status = f"[FOUND at {path}]" if path else "[NOT FOUND]"
        info += f"  - {f}: {status}\n"
    info += "-------------------------\n"
    return info

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
    """Loads configuration settings."""
    file_path = find_file(file_name)
    
    defaults = {
        "start_port": 1112,
        "rotation_enabled": True,
        "rotation_interval": 300,
        "use_key_proxy": True
    }
    
    if not file_path:
        return defaults
    
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
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
    """Loads static proxies with wide encoding support."""
    file_path = find_file(file_name)
    proxies = []
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()
        except:
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    lines = f.readlines()
            except: lines = []
                
        for line in lines:
            line = line.strip()
            if line:
                proxies.append({"type": "static", "raw": line})
    return proxies

def load_keys(file_name="key.txt"):
    """Loads rotation keys with wide encoding support."""
    file_path = find_file(file_name)
    keys = []
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()
        except:
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    lines = f.readlines()
            except: lines = []
                
        for line in lines:
            line = line.strip()
            if line:
                keys.append({"type": "api", "raw": line})
    return keys

def clear_port(port):
    """Silently attempt to clear port with a strict timeout."""
    import subprocess
    try:
        cmd = f"Stop-Process -Id (Get-NetTCPConnection -LocalPort {port}).OwningProcess -Force"
        # 5 second timeout to prevent deadlocks on slow systems
        subprocess.run(["powershell", "-Command", cmd], capture_output=True, timeout=5)
    except Exception:
        pass
