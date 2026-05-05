import os
import sys
import json
import time
import subprocess

def find_file(filename):
    if os.path.exists(filename):
        return os.path.abspath(filename)
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(base_path) == 'core':
            base_path = os.path.dirname(base_path)
    target = os.path.join(base_path, filename)
    return target if os.path.exists(target) else filename

def clear_port(port):
    """Kills any process using the specified port (Windows)."""
    try:
        output = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True).decode()
        for line in output.strip().split('\n'):
            if 'LISTENING' in line:
                pid = line.strip().split()[-1]
                subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
    except: pass

def load_config():
    path = find_file("config.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"start_port": 5555, "rotation_interval": 300}

def load_proxies():
    path = find_file("proxies.txt")
    proxies = []
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    proxies.append({"type": "static", "raw": line})
    except: pass
    return proxies

def load_keys():
    path = find_file("key.txt")
    keys = []
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line: keys.append({"type": "api", "raw": line})
    except: pass
    return keys

def format_uptime(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h}h {m}m {s}s"

def get_diagnostic_info():
    exe_path = sys.executable if getattr(sys, 'frozen', False) else __file__
    cwd = os.getcwd()
    info = f"\n--- [DIAGNOSTIC INFO] ---\n"
    info += f"EXE Path: {exe_path}\nCWD Path: {cwd}\nFile Status:\n"
    for f in ["config.json", "proxies.txt", "key.txt"]:
        p = find_file(f)
        status = "[FOUND]" if os.path.exists(p) else "[MISSING]"
        size = f"({os.path.getsize(p)} bytes)" if os.path.exists(p) else ""
        info += f"  - {f}: {status} at {p} {size}\n"
    info += "-------------------------\n"
    return info
