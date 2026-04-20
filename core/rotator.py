import aiohttp
import asyncio
import time
import base64
from rich.console import Console

console = Console()

class VuaProxyRotator:
    """Handles multi-provider API requests with VuaProxy v2 priority and direct data mapping."""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.current_upstream = None
        self.cooldown_end_time = 0
        self.last_response = {}
        self.last_error = "None"
        self.domain = self._extract_domain(api_key)
        self.confirmed_url = None
        
        # Priority 1: Official VuaProxy v2 (Applied to ALL keys first)
        self.primary_patterns = [
            "https://vuaproxy.com/api/v1/users/rotatev2?token={key}"
        ]
        
        # Priority 2: Fallback probe sequence (Only if primary fails)
        self.fallback_patterns = self._get_fallback_patterns()

    def _extract_domain(self, key):
        """Identifies the provider domain from the key payload for fallback use."""
        try:
            if "_" in key:
                prefix = key.split("_")[0]
                decoded = base64.b64decode(prefix).decode(errors='ignore')
                parts = decoded.split(";")
                for part in parts:
                    if "." in part and len(part) > 3:
                        domain = part.lower()
                        if "vuaproxy" in domain: return "vuaproxy.com"
                        return domain
            return "vuaproxy.com"
        except:
            return "vuaproxy.com"

    def _get_fallback_patterns(self):
        """Returns the probing sequence for fallback if primary VuaProxy API fails."""
        if self.domain == "vuaproxy.com":
            return ["https://api.vuaproxy.com/rotate/{key}"]
        else:
            return [
                f"http://{self.domain}/api/rotate?key={{key}}",
                f"http://{self.domain}/rotate?key={{key}}",
                f"http://{self.domain}/rotate/{{key}}",
                f"http://{self.domain}/api/v1/rotate?key={{key}}"
            ]

    def get_remaining_cooldown(self):
        """Returns the remaining seconds in the cooldown period."""
        rem = int(self.cooldown_end_time - time.time())
        return max(0, rem)

    async def rotate(self):
        """Calls the rotation API with universal high-priority for VuaProxy v2."""
        if self.get_remaining_cooldown() > 0:
            return self.current_upstream

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
        
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers, trust_env=True) as session:
            
            # Probing sequence: Confirmed URL > Primary VuaProxy v2 > Fallbacks
            if self.confirmed_url:
                urls_to_try = [self.confirmed_url]
            else:
                urls_to_try = [p.format(key=self.api_key) for p in self.primary_patterns] + \
                             [p.format(key=self.api_key) for p in self.fallback_patterns]
            
            for url in urls_to_try:
                try:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            self.last_response = data
                            
                            # Adhere to documented field: timeRemaining or wait
                            time_remaining = data.get("timeRemaining") or data.get("wait") or 0
                            self.cooldown_end_time = time.time() + int(time_remaining)
                            
                            # Success check (Accept success status or presence of proxy data)
                            success = data.get("status") == "success" or "proxy" in data or "data" in data
                            if success:
                                # Direct Mapping: Use exactly what the API provides
                                self.current_upstream = data.get("proxy") or data.get("data")
                                self.confirmed_url = url 
                                self.last_error = "None"
                                return self.current_upstream
                            else:
                                msg = data.get("message") or "API rejected request"
                                self.last_error = f"API: {msg}"
                                # If it's a known error from VuaProxy, don't try other patterns yet
                                if "vuaproxy.com" in url: return self.current_upstream
                        
                        elif resp.status == 429:
                            self.last_error = "Rate Limited"
                            return self.current_upstream
                        
                        # Handle 404/403/401 by moving to the next pattern in the list
                        if resp.status in [404, 403, 401]:
                            self.last_error = f"HTTP {resp.status} on pattern"
                            continue
                        else:
                            self.last_error = f"HTTP {resp.status}"

                except Exception as e:
                    self.last_error = str(e)[:30]
                    continue
        
        return self.current_upstream
