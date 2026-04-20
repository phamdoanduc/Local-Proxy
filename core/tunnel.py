import asyncio
import base64
import socket

class ProxyTunnel:
    """Manages a tunnel with robust DNS support and domain name handling."""
    
    def __init__(self, id, local_port, upstream_str):
        self.id = id
        self.local_port = local_port
        self.upstream_str = upstream_str
        self.status = "[yellow]WAITING[/]"
        self.auth_header = None
        self.connections = 0
        self.server = None
        
        self.upstream_host = None
        self.upstream_port = None
        self._parse_upstream(upstream_str)

    def _parse_upstream(self, s):
        try:
            # Domain Truncation for UI
            display_str = s
            if len(s) > 25:
                display_str = s[:22] + "..."
            self.upstream_str = display_str

            if "@" in s:
                auth, addr = s.split("@")
                self.upstream_host, self.upstream_port = addr.split(":")
                self.auth_header = f"Basic {base64.b64encode(auth.encode()).decode()}"
                # Update display to show domain instead of full auth string
                self.upstream_str = addr if len(addr) <= 25 else addr[:22] + "..."
            else:
                parts = s.split(":")
                if len(parts) == 4:
                    self.upstream_host, self.upstream_port = parts[0], parts[1]
                    auth = f"{parts[2]}:{parts[3]}"
                    self.auth_header = f"Basic {base64.b64encode(auth.encode()).decode()}"
                    host_port = f"{parts[0]}:{parts[1]}"
                    self.upstream_str = host_port if len(host_port) <= 25 else host_port[:22] + "..."
                else:
                    self.upstream_host, self.upstream_port = parts[0], int(parts[1])
                    host_port = f"{parts[0]}:{parts[1]}"
                    self.upstream_str = host_port if len(host_port) <= 25 else host_port[:22] + "..."
        except Exception:
            self.status = "[red]PARSE ERR[/]"

    async def _bridge(self, reader, writer):
        self.connections += 1
        target_reader, target_writer = None, None
        try:
            header_data = b""
            while b"\r\n\r\n" not in header_data:
                chunk = await reader.read(8192)
                if not chunk: break
                header_data += chunk
            
            if not header_data: return
            
            # Connect to upstream (handles both IP and Domain)
            try:
                target_reader, target_writer = await asyncio.open_connection(
                    self.upstream_host, int(self.upstream_port)
                )
            except socket.gaierror:
                self.status = "[bold red]DNS ERROR[/]"
                return
            except Exception as e:
                self.status = f"[red]CONN FAIL[/]"
                return

            # Auth injection logic
            if self.auth_header:
                try:
                    h_end = header_data.find(b"\r\n\r\n")
                    if h_end != -1:
                        header_block = header_data[:h_end]
                        body = header_data[h_end+4:]
                        header_lines = header_block.split(b"\r\n")
                        if header_lines:
                            new_header_lines = [header_lines[0]]
                            auth_line = f"Proxy-Authorization: {self.auth_header}".encode()
                            new_header_lines.append(auth_line)
                            for line in header_lines[1:]:
                                if not line.lower().startswith(b"proxy-authorization:"):
                                    new_header_lines.append(line)
                            header_data = b"\r\n".join(new_header_lines) + b"\r\n\r\n" + body
                except: pass

            target_writer.write(header_data)
            await target_writer.drain()

            async def pipe(r, w, is_upstream=False):
                try:
                    is_first = True
                    while True:
                        data = await r.read(16384)
                        if not data: break
                        if is_first and is_upstream:
                            if b"HTTP/1.1 407" in data or b"HTTP/1.0 407" in data:
                                self.status = "[bold red]AUTH FAIL (407)[/]"
                                break
                            is_first = False
                            self.status = "[green]ACTIVE[/]"
                        w.write(data)
                        await w.drain()
                except: pass
                finally:
                    try: w.close()
                    except: pass

            await asyncio.gather(
                pipe(reader, target_writer),
                pipe(target_reader, writer, is_upstream=True)
            )
        except Exception:
            pass
        finally:
            self.connections -= 1
            if writer: 
                try: writer.close()
                except: pass
            if target_writer: 
                try: target_writer.close()
                except: pass

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
