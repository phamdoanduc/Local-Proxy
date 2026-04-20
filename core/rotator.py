import aiohttp
import asyncio
import time
import base64
from rich.console import Console

console = Console()

class VuaProxyRotator:
    """Handles multi-provider API requests by dynamically parsing the rotation key."""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.current_upstream = None
        self.cooldown_end_time = 0
        self.last_response = {}
        self.api_url = self._resolve_api_url(api_key)

    def _resolve_api_url(self, key):
        """Standardizes the API URL based on the detected provider in the key."""
        try:
            # Check for domain strings in the key payload (Base64 encoded part)
            if "_" in key:
                prefix = key.split("_")[0]
                decoded = base64.b64decode(prefix).decode(errors='ignore')
                
                # Search for domain pattern in decoded string (ID;user;server)
                parts = decoded.split(";")
                for part in parts:
                    if "." in part and len(part) > 3:
                        # Found a domain like api-proxy.homeproxy.vn
                        return f"http://{part}/api/rotate?key={key}"
            
            # Default to VuaProxy official API if no domain found
            return f"https://api.vuaproxy.com/rotate/{key}"
        except:
            return f"https://api.vuaproxy.com/rotate/{key}"

    def get_remaining_cooldown(self):
        """Returns the remaining seconds in the cooldown period."""
        rem = int(self.cooldown_end_time - time.time())
        return max(0, rem)

    async def rotate(self):
        """Calls the rotation API and updates states with multi-format support."""
        if self.get_remaining_cooldown() > 0:
            return self.current_upstream

        timeout = aiohttp.ClientTimeout(total=10)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.api_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.last_response = data
                        
                        # Handle varied API response structures
                        time_remaining = data.get("timeRemaining") or data.get("wait") or 0
                        self.cooldown_end_time = time.time() + int(time_remaining)
                        
                        success = data.get("status") == "success" or "proxy" in data
                        if success:
                            self.current_upstream = data.get("proxy") or data.get("data")
                            return self.current_upstream
                        
                    # Handle 429 or other non-200 responses with wait time
                    elif resp.status == 429:
                        try:
                            data = await resp.json()
                            wait = data.get("wait") or 60
                            self.cooldown_end_time = time.time() + wait
                        except: pass
                        
                    return self.current_upstream
        except Exception:
            return self.current_upstream
