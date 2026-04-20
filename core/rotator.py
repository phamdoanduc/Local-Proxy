import aiohttp
import asyncio
import time

class VuaProxyRotator:
    """Handles API requests to VuaProxy to rotate and fetch proxy status."""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_url = f"https://api.vuaproxy.com/rotate/{api_key}"
        self.current_upstream = None
        self.cooldown_end_time = 0
        self.last_response = {}

    def get_remaining_cooldown(self):
        """Returns the remaining seconds in the cooldown period."""
        rem = int(self.cooldown_end_time - time.time())
        return max(0, rem)

    async def rotate(self):
        """Calls the rotation API and updates the proxy URL and cooldown state."""
        # Check local cooldown first
        if self.get_remaining_cooldown() > 0:
            return self.current_upstream

        timeout = aiohttp.ClientTimeout(total=10) # 10 second timeout
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.api_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.last_response = data
                        
                        # Sync cooldown from API response
                        time_remaining = data.get("timeRemaining", 0)
                        self.cooldown_end_time = time.time() + time_remaining
                        
                        if data.get("status") == "success":
                            self.current_upstream = data.get("proxy")
                            return self.current_upstream
                    return self.current_upstream # Fallback to existing
        except Exception:
            return self.current_upstream # Keep current on network error
