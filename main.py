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
from rich import box

console = Console()

def generate_dashboard(manager, start_time, page=0, page_size=10):
    uptime = format_uptime(time.time() - start_time)
    mode_str = "[STATIC MODE]" if not manager.config.get("use_key_proxy", False) else "[KEY MODE]"
    
    total_tunnels = len(manager.tunnels)
    total_pages = (total_tunnels + page_size - 1) // page_size
    current_page = page % total_pages if total_pages > 0 else 0
    
    start_idx = current_page * page_size
    end_idx = min(start_idx + page_size, total_tunnels)
    display_tunnels = manager.tunnels[start_idx:end_idx]

    table = Table(
        title=f"VuaProxy - Local Proxy {mode_str} - Up: {uptime} (Page {current_page+1}/{total_pages if total_pages > 0 else 1})",
        box=box.ROUNDED,
        header_style="bold cyan",
        expand=True
    )
    
    table.add_column("ID", justify="center", style="dim")
    table.add_column("LOCAL GATEWAY", justify="left", style="green")
    table.add_column("API IP:PORT", justify="left", style="white")
    table.add_column("STATUS", justify="center")
    table.add_column("COOLDOWN", justify="center", style="yellow")
    table.add_column("CONNS", justify="center", style="magenta")

    for tunnel in display_tunnels:
        status_text = manager.get_rotation_status(tunnel)
        color = "green" if "READY" in status_text or "WAIT" in status_text else "white"
        if "LAG" in status_text: color = "bold red"
        
        table.add_row(
            str(tunnel.id),
            f"127.0.0.1:{tunnel.target_port}",
            tunnel.upstream_addr if tunnel.upstream_addr else "0.0.0.0:0",
            "[bold green]ACTIVE[/]",
            f"[{color}]{status_text}[/]",
            str(getattr(tunnel, 'connection_count', 0))
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
        
        console.print("[bold green][*] Initializing VuaProxy Core v6.5.3 [Pure Gold]...[/]")
        
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
