import aiohttp
import asyncio
import time

class VuaProxyRotator:
    """Handles API requests to VuaProxy for IP rotation."""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://vuaproxy.com/api/v1/users/rotatev2"
        self.last_proxy = None
        self.next_rotate_allowed = 0
        self.status = "IDLE"

    async def rotate(self, check_only=False):
        """Calls the rotation API."""
        url = f"{self.base_url}?token={self.api_key}"
        if check_only:
            url += "&checkOnly=true"
            
        self.status = "ROTATING..."
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Always sync cooldown if timeRemaining is present
                        if "timeRemaining" in data:
                            self.next_rotate_allowed = time.time() + int(data["timeRemaining"])

                        if data.get("status") == "success":
                            self.last_proxy = data.get("proxy")
                            self.status = "SUCCESS"
                            return self.last_proxy
                        else:
                            msg = data.get("message", "FAILED")
                            self.status = f"ERR: {msg[:15]}"
                    else:
                        self.status = f"HTTP {response.status}"
        except Exception as e:
            self.status = f"ERR: {str(e)[:15]}"
        
        return None

    def get_remaining_cooldown(self):
        """Returns seconds until next rotation is allowed."""
        rem = self.next_rotate_allowed - time.time()
        return max(0, int(rem))
