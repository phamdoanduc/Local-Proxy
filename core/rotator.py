import aiohttp
import asyncio
import time
import base64
from rich.console import Console

console = Console()

class VuaProxyRotator:
    """Handles multi-provider API requests with intelligent pattern probing."""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.current_upstream = None
        self.cooldown_end_time = 0
        self.last_response = {}
        self.last_error = "None"
        self.domain = self._extract_domain(api_key)
        self.confirmed_url = None
        
        # Common patterns to probe if 404 is encountered
        self.patterns = [
            "/api/rotate?key={key}",
            "/rotate?key={key}",
            "/rotate/{key}",
            "/api/v1/rotate?key={key}",
            "/index.php?key={key}&action=rotate"
        ]

    def _extract_domain(self, key):
        """Identifies the provider domain from the key payload."""
        try:
            if "_" in key:
                prefix = key.split("_")[0]
                decoded = base64.b64decode(prefix).decode(errors='ignore')
                parts = decoded.split(";")
                for part in parts:
                    if "." in part and len(part) > 3:
                        return part
            return "api.vuaproxy.com"
        except:
            return "api.vuaproxy.com"

    def get_remaining_cooldown(self):
        """Returns the remaining seconds in the cooldown period."""
        rem = int(self.cooldown_end_time - time.time())
        return max(0, rem)

    async def rotate(self):
        """Calls the rotation API with intelligent pattern probing for 404 errors."""
        if self.get_remaining_cooldown() > 0:
            return self.current_upstream

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
        
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers, trust_env=True) as session:
            
            # If we already found a working URL, use it directly
            urls_to_try = [self.confirmed_url] if self.confirmed_url else [
                f"http://{self.domain}{p.format(key=self.api_key)}" for p in self.patterns
            ]
            
            for url in urls_to_try:
                try:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            self.last_response = data
                            
                            time_remaining = data.get("timeRemaining") or data.get("wait") or 0
                            self.cooldown_end_time = time.time() + int(time_remaining)
                            
                            success = data.get("status") == "success" or "proxy" in data or "data" in data
                            if success:
                                self.current_upstream = data.get("proxy") or data.get("data")
                                self.confirmed_url = url # Save the working pattern
                                self.last_error = "None"
                                return self.current_upstream
                        
                        elif resp.status == 429:
                            self.last_error = "Rate Limited"
                            try:
                                data = await resp.json()
                                wait = data.get("wait") or 60
                                self.cooldown_end_time = time.time() + wait
                                return self.current_upstream
                            except: pass
                            
                        # If 404, we continue to the next pattern
                        if resp.status == 404:
                            self.last_error = f"HTTP 404 on {url.split('?')[0]}"
                            continue
                        else:
                            self.last_error = f"HTTP {resp.status}"

                except Exception as e:
                    self.last_error = str(e)[:30]
                    continue
        
        return self.current_upstream
