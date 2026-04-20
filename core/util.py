import json
import os
import sys
import re
from rich.console import Console

console = Console()

def find_file(filename):
    """Finds a file in multiple locations to ensure portability."""
    # 1. Check same directory as the EXE/Script
    exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    # 2. Check current working directory
    cwd = os.getcwd()
    
    search_paths = [exe_dir, cwd]
    
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
        # Standard parse
        return json.loads(content)
    except json.JSONDecodeError as e:
        # Try to fix common trailing comma or missing comma issues (Basic Attempt)
        try:
            # Remove trailing commas
            fixed = re.sub(r',\s*([\]}])', r'\1', content)
            return json.loads(fixed)
        except:
            console.print(f"[bold red][!] Config Error in config.json at line {e.lineno}, col {e.colno}[/]")
            console.print(f"[yellow][?] Hint: Make sure every line has a comma except the last one.[/]")
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

def clear_port(port):
    """Clears a port using a non-blocking PowerShell command with timeout."""
    import subprocess
    cmd = f"Stop-Process -Id (Get-NetTCPConnection -LocalPort {port}).OwningProcess -Force"
    try:
        subprocess.run(["powershell", "-Command", cmd], capture_output=True, timeout=5)
    except:
        pass
