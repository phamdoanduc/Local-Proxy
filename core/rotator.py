import aiohttp
import asyncio
import time
import base64
import socket
from rich.console import Console

console = Console()

class VuaProxyRotator:
    """Handles multi-provider API requests with detailed diagnostic reporting."""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.current_upstream = None
        self.cooldown_end_time = 0
        self.last_response = {}
        self.last_error = "None"
        self.api_url = self._resolve_api_url(api_key)

    def _resolve_api_url(self, key):
        """Standardizes the API URL and identifies the provider domain."""
        try:
            if "_" in key:
                prefix = key.split("_")[0]
                decoded = base64.b64decode(prefix).decode(errors='ignore')
                parts = decoded.split(";")
                for part in parts:
                    if "." in part and len(part) > 3:
                        return f"http://{part}/api/rotate?key={key}"
            return f"https://api.vuaproxy.com/rotate/{key}"
        except:
            return f"https://api.vuaproxy.com/rotate/{key}"

    def get_remaining_cooldown(self):
        """Returns the remaining seconds in the cooldown period."""
        rem = int(self.cooldown_end_time - time.time())
        return max(0, rem)

    async def rotate(self):
        """Calls the rotation API with detailed error catching and UA spoofing."""
        if self.get_remaining_cooldown() > 0:
            return self.current_upstream

        # Browser-like headers to avoid being blocked
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
        
        timeout = aiohttp.ClientTimeout(total=10)
        # Use trust_env=True to inherit system proxy/cert settings if needed
        async with aiohttp.ClientSession(timeout=timeout, headers=headers, trust_env=True) as session:
            try:
                async with session.get(self.api_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.last_response = data
                        
                        time_remaining = data.get("timeRemaining") or data.get("wait") or 0
                        self.cooldown_end_time = time.time() + int(time_remaining)
                        
                        success = data.get("status") == "success" or "proxy" in data
                        if success:
                            self.current_upstream = data.get("proxy") or data.get("data")
                            self.last_error = "None"
                            return self.current_upstream
                        else:
                            msg = data.get("message") or data.get("error") or "Unknown API Error"
                            self.last_error = f"API Message: {msg}"
                    elif resp.status == 429:
                        self.last_error = "Rate Limited (Wait Cooldown)"
                        try:
                            data = await resp.json()
                            wait = data.get("wait") or 60
                            self.cooldown_end_time = time.time() + wait
                        except: pass
                    elif resp.status == 403:
                        self.last_error = "403 Forbidden (Check IP Whitelist)"
                    elif resp.status == 401:
                        self.last_error = "401 Unauthorized (Invalid Key)"
                    else:
                        self.last_error = f"HTTP {resp.status}"
            except aiohttp.ClientConnectorError:
                self.last_error = "Connection Failed (Check Firewall/Internet)"
            except asyncio.TimeoutError:
                self.last_error = "API Timeout (Server Not Responding)"
            except Exception as e:
                self.last_error = str(e)[:30]
        
        return self.current_upstream
