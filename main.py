import asyncio
import time
import sys
from rich.live import Live
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from core.manager import ProxyManager
from core.util import format_uptime, get_diagnostic_info

console = Console()

def generate_dashboard(manager, start_time):
    """Generates the live dashboard table with unified rotation timing."""
    uptime = format_uptime(time.time() - start_time)
    mode = "[KEY MODE]" if manager.config.get("use_key_proxy") else "[STATIC MODE]"
    
    table = Table(title=f"VuaProxy - Local Proxy {mode} - Up: {uptime}", expand=True)
    table.add_column("ID", justify="center", style="cyan", no_wrap=True)
    table.add_column("LOCAL GATEWAY", justify="left", style="white")
    table.add_column("API IP:PORT", justify="left", style="magenta")
    table.add_column("STATUS", justify="center", style="green")
    table.add_column("COOLDOWN", justify="center", style="yellow")
    table.add_column("CONNS", justify="center", style="white")

    for tunnel in manager.tunnels:
        status = "ACTIVE" if tunnel.is_active else "ERROR"
        status_style = "green" if tunnel.is_active else "bold red"
        
        # Use the unified rotation status from manager
        cooldown_display = manager.get_rotation_status(tunnel)
        
        table.add_row(
            str(tunnel.id),
            f"127.0.0.1:{tunnel.target_port}",
            tunnel.upstream_addr if tunnel.upstream_addr else "0.0.0.0:0",
            f"[{status_style}]{status}[/]",
            cooldown_display,
            str(tunnel.connection_count)
        )
    return table

async def handle_input(manager):
    """Handles async keyboard input for manual rotation and quit."""
    import msvcrt
    while manager.is_running:
        if msvcrt.kbhit():
            key = msvcrt.getch().decode('utf-8').lower()
            if key == 'r':
                await manager.rotate_all()
            elif key == 'q':
                await manager.stop_all()
                break
        await asyncio.sleep(0.1)

async def main():
    try:
        manager = ProxyManager()
        start_time = time.time()
        
        console.print("[bold green][*] Initializing VuaProxy Core v6.3.1 [Clean Bridge]...[/]")
        
        # Start all tunnels once
        await manager.start_all()
        
        if not manager.tunnels:
            console.print("[bold red][!] No proxies found. Please check your config and data files.[/]")
            console.print(get_diagnostic_info())
            input("\nPress Enter to exit...")
            return

        console.print("[dim italic]Controls: [R] Manual Rotate All | [Q] Safe Quit[/]")

        input_task = asyncio.create_task(handle_input(manager))
        
        with Live(generate_dashboard(manager, start_time), refresh_per_second=1) as live:
            while not input_task.done():
                live.update(generate_dashboard(manager, start_time))
                await asyncio.sleep(1)
                
    except KeyboardInterrupt:
        await manager.stop_all()
    except Exception as e:
        console.print(f"[bold red][FATAL ERROR] {e}[/]")
        from core.util import get_diagnostic_info
        console.print(get_diagnostic_info())
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit and check logs...")
    finally:
        console.print("[bold yellow][*] VuaProxy Engine stopped.[/]")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
