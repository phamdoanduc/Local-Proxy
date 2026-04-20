import asyncio
import base64

class ProxyTunnel:
    """Manages a single tunnel from a local port to an upstream proxy."""
    
    def __init__(self, id, local_port, upstream_str):
        self.id = id
        self.local_port = local_port
        self.upstream_str = upstream_str # IP:PORT for display
        self.status = "[yellow]WAITING[/]"
        self.auth_header = None
        self.connections = 0
        self.server = None
        
        self.upstream_host = None
        self.upstream_port = None
        self._parse_upstream(upstream_str)

    def _parse_upstream(self, s):
        try:
            if "@" in s:
                auth, addr = s.split("@")
                self.upstream_host, self.upstream_port = addr.split(":")
                self.auth_header = f"Basic {base64.b64encode(auth.encode()).decode()}"
                self.upstream_str = addr
            else:
                parts = s.split(":")
                if len(parts) == 4:
                    self.upstream_host, self.upstream_port = parts[0], parts[1]
                    auth = f"{parts[2]}:{parts[3]}"
                    self.auth_header = f"Basic {base64.b64encode(auth.encode()).decode()}"
                    self.upstream_str = f"{parts[0]}:{parts[1]}"
                else:
                    self.upstream_host, self.upstream_port = parts[0], int(parts[1])
                    self.upstream_str = f"{parts[0]}:{parts[1]}"
        except Exception:
            self.status = "[red]PARSE ERR[/]"

    async def _bridge(self, reader, writer):
        self.connections += 1
        target_reader, target_writer = None, None
        try:
            header_data = await reader.read(8192)
            if not header_data: return
            
            target_reader, target_writer = await asyncio.open_connection(
                self.upstream_host, int(self.upstream_port)
            )

            if self.auth_header:
                header_text = header_data.decode(errors='ignore')
                if "Proxy-Authorization" not in header_text:
                    lines = header_text.split("\r\n")
                    if len(lines) > 1:
                        lines.insert(1, f"Proxy-Authorization: {self.auth_header}")
                        header_data = "\r\n".join(lines).encode()

            target_writer.write(header_data)
            await target_writer.drain()

            async def pipe(r, w):
                try:
                    while True:
                        data = await r.read(8192)
                        if not data: break
                        w.write(data)
                        await w.drain()
                except: pass
                finally:
                    try: w.close()
                    except: pass

            await asyncio.gather(
                pipe(reader, target_writer),
                pipe(target_reader, writer)
            )
        except Exception:
            pass
        finally:
            self.connections -= 1
            if writer: writer.close()
            if target_writer: target_writer.close()

    async def start(self):
        if not self.upstream_host:
            return False
        try:
            self.server = await asyncio.start_server(self._bridge, '127.0.0.1', self.local_port)
            self.status = "[green]ACTIVE[/]"
            return True
        except Exception as e:
            self.status = f"[red]ERR: {str(e)[:15]}[/]"
            return False

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.status = "[white]CLOSED[/]"
