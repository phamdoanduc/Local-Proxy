import asyncio
import sys
import time
from rich.console import Console
from rich.table import Table
from rich.live import Live

from core.manager import ProxyManager
from core.util import format_uptime

console = Console()

def generate_dashboard(manager, start_time):
    """Generates the Rich table for the dashboard."""
    uptime = time.time() - start_time
    use_key = manager.config.get("use_key_proxy", True)
    mode = "[KEY MODE]" if use_key else "[STATIC MODE]"
    
    table = Table(
        title=f"VuaProxy - Local Proxy {mode} - Up: {format_uptime(uptime)}", 
        border_style="bright_blue", 
        title_style="bold cyan"
    )
    
    table.add_column("ID", justify="center", style="dim")
    table.add_column("LOCAL GATEWAY", style="bright_white bold")
    table.add_column("API IP:PORT", style="green bold")
    table.add_column("STATUS", justify="center")
    table.add_column("COOLDOWN", justify="center", style="yellow")
    table.add_column("CONNS", justify="right")
    
    for t in manager.tunnels:
        cooldown = "N/A"
        if hasattr(t, 'rotator'):
            rem = t.rotator.get_remaining_cooldown()
            cooldown = f"{rem}s" if rem > 0 else "[green]READY[/]"
            
        table.add_row(
            str(t.id),
            f"127.0.0.1:{t.local_port}",
            str(t.upstream_str),
            t.status,
            cooldown,
            str(t.connections)
        )
    return table

async def handle_input(manager):
    """Listens for keyboard input without blocking."""
    import msvcrt
    while True:
        try:
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8').lower()
                if key == 'r':
                    await manager.rotate_all_manual()
                elif key == 'q':
                    return "QUIT"
        except: pass
        await asyncio.sleep(0.1)

async def main():
    try:
        manager = ProxyManager()
        start_time = time.time()
        
        console.print("[bold green][*] Initializing VuaProxy Core v5.6 [API Hunter]...[/]")
        
        # Start all tunnels once
        await manager.start_all()
        
        if not manager.tunnels:
            console.print("[bold red][!] No proxies found. Please check your config and data files.[/]")
            from core.util import get_diagnostic_info
            console.print(get_diagnostic_info())
            input("\nPress Enter to exit...")
            return

        console.print("[dim italic]Controls: [R] Manual Rotate All | [Q] Safe Quit[/]")

        input_task = asyncio.create_task(handle_input(manager))
        
        with Live(generate_dashboard(manager, start_time), refresh_per_second=2) as live:
            while not input_task.done():
                live.update(generate_dashboard(manager, start_time))
                await asyncio.sleep(0.5)
            
            if input_task.result() == "QUIT":
                pass
                
    except Exception as e:
        console.print(f"\n[bold red][FATAL ERROR] {str(e)}[/]")
        import traceback
        console.print(traceback.format_exc())
        input("\nPress Enter to exit and check logs...")
    finally:
        console.print("\n[yellow][*] Shutting down Core Engine...[/]")
        await manager.stop_all()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
