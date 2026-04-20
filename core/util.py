import json
import os
import sys
import re
import time
import socket
from rich.console import Console

console = Console()

def format_uptime(seconds):
    """Converts seconds into a human-readable Hh Mm Ss format."""
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}h {m}m {s}s"

def find_file(filename):
    """Finds a file prioritizing the directory of the current script/EXE."""
    # 1. Absolute Priority: Directory where the current running process lives
    exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    # 2. Secondary: Current Working Directory
    cwd = os.getcwd()
    
    search_paths = [exe_dir, cwd]
    
    # Remove duplicates
    search_paths = list(dict.fromkeys(search_paths))
    
    for path in search_paths:
        full_path = os.path.join(path, filename)
        if os.path.exists(full_path):
            return full_path
    return None

def read_file_safe(path):
    """Reads a file trying multiple encodings to ensure compatibility with all editors."""
    encodings = ['utf-8-sig', 'utf-8', 'utf-16', 'latin-1', 'cp1252']
    for enc in encodings:
        try:
            with open(path, 'r', encoding=enc) as f:
                return f.read()
        except:
            continue
    return ""

def load_config():
    """Loads config.json with smart error reporting and syntax tolerance."""
    path = find_file("config.json")
    if not path:
        return {}
    content = read_file_safe(path)
    if not content: return {}
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        try:
            fixed = re.sub(r',\s*([\]}])', r'\1', content)
            return json.loads(fixed)
        except:
            console.print(f"[bold red][!] Config Error in config.json at line {e.lineno}, col {e.colno}[/]")
            return {}
    except:
        return {}

def load_proxies():
    """Loads proxies from proxies.txt with multi-encoding support."""
    path = find_file("proxies.txt")
    if not path: return []
    content = read_file_safe(path)
    if not content: return []
    lines = []
    for line in content.splitlines():
        cleaned = line.strip()
        if cleaned:
            lines.append({"type": "static", "raw": cleaned})
    return lines

def load_keys():
    """Loads rotation keys from key.txt with multi-encoding support."""
    path = find_file("key.txt")
    if not path: return []
    content = read_file_safe(path)
    if not content: return []
    lines = []
    for line in content.splitlines():
        cleaned = line.strip()
        if cleaned:
            lines.append({"type": "api", "raw": cleaned})
    return lines

def get_diagnostic_info():
    """Provides a detailed diagnostic report with file sizes to identify empty files."""
    exe_path = sys.argv[0]
    cwd = os.getcwd()
    
    report = "\n--- [DIAGNOSTIC INFO] ---\n"
    report += f"EXE Path: {exe_path}\n"
    report += f"CWD Path: {cwd}\n"
    report += "File Status:\n"
    
    for f in ["config.json", "proxies.txt", "key.txt"]:
        p = find_file(f)
        if p:
            size = os.path.getsize(p)
            report += f"  - {f}: [FOUND at {p}] ({size} bytes)\n"
        else:
            report += f"  - {f}: [NOT FOUND]\n"
    
    report += "-------------------------\n"
    return report

def clear_port(port):
    """Clears a port using a non-blocking PowerShell command with timeout."""
    import subprocess
    cmd = f"Stop-Process -Id (Get-NetTCPConnection -LocalPort {port}).OwningProcess -Force"
    try:
        subprocess.run(["powershell", "-Command", cmd], capture_output=True, timeout=5)
    except:
        pass
