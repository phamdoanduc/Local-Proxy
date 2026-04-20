import asyncio
from core.tunnel import ProxyTunnel
from core.util import load_config, load_proxies

class ProxyManager:
    """Orchestrates multiple proxy tunnels with granular logging and timeouts."""
    
    def __init__(self):
        self.tunnels = []
        self.config = load_config()
        self.start_port = self.config.get("start_port", 1112)
        self.is_running = False

    def reload_data(self):
        """Reloads config from disk."""
        self.config = load_config()
        self.start_port = self.config.get("start_port", 1112)

    async def start_all(self):
        """Initializes and starts tunnels with step-by-step progress tracking."""
        from core.util import clear_port, load_proxies, load_keys
        from core.rotator import VuaProxyRotator
        from rich.console import Console
        console = Console()
        
        self.tunnels = []
        use_key = self.config.get("use_key_proxy", True)
        all_proxies = load_keys() if use_key else load_proxies()
        
        console.print(f"[*] Found {len(all_proxies)} proxy configurations.")
        
        for i, info in enumerate(all_proxies):
            tunnel_id = i + 1
            target_port = self.start_port + i
            raw = info["raw"]
            
            console.print(f"[dim]=> [{tunnel_id}] Initializing port {target_port}...[/]")
            
            try:
                if info["type"] == "api" or raw.startswith("API|"):
                    api_key = raw.replace("API|", "")
                    rotator = VuaProxyRotator(api_key)
                    
                    console.print(f"[dim]   > [{tunnel_id}] Requesting IP from API...[/]")
                    try:
                        # API call with internal timeout from rotator.py
                        upstream = await rotator.rotate()
                    except:
                        upstream = None
                        
                    if not upstream: 
                        console.print(f"[red]   ! [{tunnel_id}] API Request Failed. Using dummy IP.[/]")
                        upstream = "0.0.0.0:0"
                    
                    tunnel = ProxyTunnel(tunnel_id, target_port, upstream)
                    tunnel.rotator = rotator
                else:
                    tunnel = ProxyTunnel(tunnel_id, target_port, raw)
                
                console.print(f"[dim]   > [{tunnel_id}] Clearing existing port {target_port}...[/]")
                clear_port(target_port)
                
                console.print(f"[dim]   > [{tunnel_id}] Starting Gateway...[/]")
                success = await tunnel.start()
                
                if success:
                    self.tunnels.append(tunnel)
                    console.print(f"[green]   + [{tunnel_id}] Started Successfully.[/]")
                else:
                    console.print(f"[red]   - [{tunnel_id}] Gateway Start Failed.[/]")
                    
            except Exception as e:
                console.print(f"[bold red]   !!! [{tunnel_id}] Fatal Error: {str(e)}[/]")

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
                        try:
                            new_upstream = await tunnel.rotator.rotate()
                            if new_upstream:
                                tunnel._parse_upstream(new_upstream)
                        except: pass

    async def rotate_all_manual(self):
        """Forces a manual rotation cycle for all API-based tunnels."""
        tasks = []
        for tunnel in self.tunnels:
            if hasattr(tunnel, 'rotator'):
                tasks.append(tunnel.rotator.rotate())
        
        if not tasks: return
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        api_tunnels = [t for t in self.tunnels if hasattr(t, 'rotator')]
        
        for i, new_upstream in enumerate(results):
            if isinstance(new_upstream, str) and new_upstream and i < len(api_tunnels):
                api_tunnels[i]._parse_upstream(new_upstream)

    async def stop_all(self):
        """Stops all running tunnels."""
        for tunnel in self.tunnels:
            await tunnel.stop()
        self.is_running = False
