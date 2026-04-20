import json
import os

def load_config(file_path="config.json"):
    """Loads configuration settings from a JSON file."""
    if not os.path.exists(file_path):
        return {
            "rotation_interval": 300,
            "rotation_enabled": False,
            "use_key_proxy": True,
            "token_proxy_port": 9898
        }
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            start_port = config.get("start_port", 8001)
            # Port Validation
            if not (1 <= start_port <= 65535):
                start_port = 8001
            
            return {
                "start_port": start_port,
                "rotation_interval": config.get("rotation_interval", 300),
                "rotation_enabled": config.get("rotation_enabled", False),
                "use_key_proxy": config.get("use_key_proxy", True),
                "token_proxy_port": config.get("token_proxy_port", 9898)
            }
    except Exception:
        return {"start_port": 8001}

def load_proxies(file_path="proxies.txt"):
    """Loads static proxies from proxies.txt."""
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# Static Proxies: ip:port:user:pass\n")
        return []
    
    proxies = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                proxies.append({"type": "static", "raw": line})
        return proxies
    except Exception:
        return []

def load_keys(file_path="key.txt"):
    """Loads rotating keys from key.txt."""
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# Rotating Keys (VuaProxy or HomeProxy)\n")
        return []
    
    keys = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                keys.append({"type": "api", "raw": line})
        return keys
    except Exception:
        return []

def format_uptime(seconds):
    """Utility to format seconds into a human-readable string."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h}h {m}m {s}s"

def clear_port(port):
    """Checks for a process on a port and kills it (Windows specific)."""
    import subprocess
    try:
        # Find the PID using the port
        cmd = f'netstat -ano | findstr :{port}'
        output = subprocess.check_output(cmd, shell=True).decode()
        for line in output.strip().split('\n'):
            if 'LISTENING' in line:
                pid = line.strip().split()[-1]
                if pid != '0':
                    # Kill the process
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                    return True
    except Exception:
        pass
    return False
