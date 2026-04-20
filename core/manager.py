import asyncio
from core.tunnel import ProxyTunnel
from core.util import load_config, load_proxies

class ProxyManager:
    """Orchestrates multiple proxy tunnels and handles background rotation."""
    
    def __init__(self):
        self.tunnels = []
        self.config = load_config()
        self.start_port = self.config.get("start_port", 8001)
        self.is_running = False

    def reload_data(self):
        """Reloads config from disk."""
        self.config = load_config()
        self.start_port = self.config.get("start_port", 8001)

    async def start_all(self):
        """Initializes and starts all tunnels from the chosen source."""
        from core.util import clear_port, load_proxies, load_keys
        from core.rotator import VuaProxyRotator
        self.tunnels = []
        
        # Select data source based on config
        use_key = self.config.get("use_key_proxy", True)
        all_proxies = load_keys() if use_key else load_proxies()
        
        mode_str = "KEY MODE" if use_key else "STATIC MODE"
        print(f"[*] Starting in {mode_str}...")
        
        for i, info in enumerate(all_proxies):
            raw = info["raw"]
            target_port = self.start_port + i
            
            if info["type"] == "api" or raw.startswith("API|"):
                api_key = raw.replace("API|", "")
                rotator = VuaProxyRotator(api_key)
                
                print(f"[*] Initial rotation for Key on Port {target_port}...")
                upstream = await rotator.rotate()
                if not upstream: upstream = "0.0.0.0:0"
                
                tunnel = ProxyTunnel(i + 1, target_port, upstream)
                tunnel.rotator = rotator
            else:
                tunnel = ProxyTunnel(i + 1, target_port, raw)
            
            clear_port(target_port)
            await tunnel.start()
            self.tunnels.append(tunnel)
        
        # Start background rotation task if enabled
        if self.config.get("rotation_enabled"):
            asyncio.create_task(self._rotation_loop())
        
        self.is_running = True

    async def _rotation_loop(self):
        """Background task to periodically rotate API-based proxies."""
        while self.is_running:
            await asyncio.sleep(10)
            for tunnel in self.tunnels:
                if hasattr(tunnel, 'rotator'):
                    if tunnel.rotator.get_remaining_cooldown() == 0:
                        print(f"[*] Auto-Rotating Port {tunnel.local_port}...")
                        new_upstream = await tunnel.rotator.rotate()
                        if new_upstream:
                            tunnel._parse_upstream(new_upstream)

    async def rotate_all_manual(self):
        """Forces a manual rotation cycle for all API-based tunnels."""
        tasks = []
        for tunnel in self.tunnels:
            if hasattr(tunnel, 'rotator'):
                tasks.append(tunnel.rotator.rotate())
        
        results = await asyncio.gather(*tasks)
        for i, new_upstream in enumerate(results):
            if new_upstream:
                api_tunnels = [t for t in self.tunnels if hasattr(t, 'rotator')]
                if i < len(api_tunnels):
                    api_tunnels[i]._parse_upstream(new_upstream)

    async def stop_all(self):
        """Stops all running tunnels."""
        for tunnel in self.tunnels:
            await tunnel.stop()
        self.is_running = False
