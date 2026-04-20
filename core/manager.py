import asyncio
import time
import socket
from rich.console import Console
from core.tunnel import ProxyTunnel
from core.rotator import VuaProxyRotator
from core.util import load_config, load_proxies, load_keys, clear_port

console = Console()

class ProxyManager:
    """Manages tunnels with integrated 'Exit Latency' monitoring to detect poor proxy performance."""
    
    def __init__(self):
        self.tunnels = []
        self.is_running = True
        self.config = load_config()
        self.rotation_enabled = self.config.get("rotation_enabled", False)
        self.rotation_interval = self.config.get("rotation_interval", 300)
        self._loop_task = None
        self._health_task = None

    async def start_all(self):
        """Initializes tunnels and starts background monitoring tasks."""
        self.tunnels = []
        use_key = self.config.get("use_key_proxy", False)
        
        proxy_data = load_keys() if use_key else load_proxies()
        start_port = self.config.get("start_port", 5555)

        for i, item in enumerate(proxy_data):
            tunnel_id = i + 1
            target_port = start_port + i
            
            console.print(f"[bold blue]=> [{tunnel_id}] Initializing port {target_port}...[/]")
            
            try:
                clear_port(target_port)
                upstream = item.get("raw")
                rotator = None
                
                if item.get("type") == "api":
                    console.print(f"   > [{tunnel_id}] Requesting IP from API...")
                    rotator = VuaProxyRotator(upstream)
                    upstream = await rotator.rotate()
                
                tunnel = ProxyTunnel(tunnel_id, target_port, upstream)
                if rotator: 
                    tunnel.rotator = rotator
                    tunnel.last_rotation_time = time.time()
                
                if await tunnel.start():
                    self.tunnels.append(tunnel)
                    console.print(f"   [green]+ [{tunnel_id}] Started Successfully.[/]")
            except Exception as e:
                console.print(f"   [bold red][!] Failed: {e}[/]")

        if self.rotation_enabled:
            self._loop_task = asyncio.create_task(self._rotation_loop())
            self._health_task = asyncio.create_task(self._health_check_loop())

    def get_rotation_status(self, tunnel):
        """Returns visual timing or latency-based health status."""
        if not hasattr(tunnel, 'rotator'):
            return "N/A"
        
        if getattr(tunnel, 'is_lagging', False):
            return "[bold red]LAG (Rotating...)[/]"

        current_time = time.time()
        elapsed = current_time - getattr(tunnel, 'last_rotation_time', 0)
        wait_interval = int(self.rotation_interval - elapsed)
        
        if wait_interval > 0:
            return f"WAIT {wait_interval}s"
        
        api_wait = tunnel.rotator.get_remaining_cooldown()
        return f"API WAIT {api_wait}s" if api_wait > 0 else "READY"

    async def _health_check_loop(self):
        """Monitors real internet throughput (Exit Latency) for each proxy."""
        while self.is_running:
            await asyncio.sleep(20) # Check every 20 seconds
            for tunnel in self.tunnels:
                if hasattr(tunnel, 'rotator') and hasattr(tunnel, 'upstream_host'):
                    try:
                        start = time.perf_counter()
                        # Test End-to-End Handshake through the proxy to Cloudflare DNS
                        loop = asyncio.get_event_loop()
                        
                        def probe_exit():
                            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                                s.settimeout(5.0) # 5 second exit threshold
                                s.connect((tunnel.upstream_host, int(tunnel.upstream_port)))
                                
                                # Send proxy handshake to test exit internet speed
                                auth_line = f"Proxy-Authorization: {tunnel.auth_header}\r\n" if tunnel.auth_header else ""
                                handshake = f"CONNECT 1.1.1.1:80 HTTP/1.1\r\n{auth_line}\r\n"
                                s.sendall(handshake.encode())
                                
                                # Wait for response
                                resp = s.recv(1024).decode(errors='ignore')
                                return "200" in resp.split("\r\n")[0]

                        success = await loop.run_in_executor(None, probe_exit)
                        
                        if success:
                            latency = int((time.perf_counter() - start) * 1000)
                            tunnel.last_ping = latency
                            tunnel.is_lagging = False
                        else:
                            raise Exception("Proxy Exit Denied")

                    except Exception:
                        # Failed or exit latency > 5s
                        tunnel.last_ping = 9999
                        tunnel.is_lagging = True
                        console.print(f"[bold red][!] Gate {tunnel.id} Exit Lag! Rotating IP...[/]")
                        await self._rotate_single(tunnel, force=True)

    async def _rotate_single(self, tunnel, force=False):
        """Rotates upstream proxy, enforcing user intervals unless forced."""
        current_time = time.time()
        elapsed = current_time - getattr(tunnel, 'last_rotation_time', 0)
        
        if not force and elapsed < self.rotation_interval:
            return

        if tunnel.rotator.get_remaining_cooldown() == 0:
            new_upstream = await tunnel.rotator.rotate()
            if new_upstream:
                tunnel.update_upstream(new_upstream)
                tunnel.last_rotation_time = current_time
                tunnel.is_lagging = False

    async def _rotation_loop(self):
        """Rotation loop."""
        while self.is_running:
            await asyncio.sleep(1)
            if self.rotation_enabled:
                for tunnel in self.tunnels:
                    if hasattr(tunnel, 'rotator'):
                        await self._rotate_single(tunnel)

    async def stop_all(self):
        """Cleanup."""
        self.is_running = False
        if self._loop_task: self._loop_task.cancel()
        if self._health_task: self._health_task.cancel()
        for tunnel in self.tunnels: await tunnel.stop()
