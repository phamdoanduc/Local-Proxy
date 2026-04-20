import asyncio
import base64

class ProxyTunnel:
    """Manages a tunnel with byte-perfect transparent proxy authentication."""
    
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
            # Read until full header block is received
            header_data = b""
            while b"\r\n\r\n" not in header_data:
                chunk = await reader.read(8192)
                if not chunk: break
                header_data += chunk
            
            if not header_data: return
            
            # Connect to upstream
            target_reader, target_writer = await asyncio.open_connection(
                self.upstream_host, int(self.upstream_port)
            )

            # Hyper Transparent Byte Injection
            if self.auth_header:
                try:
                    # 1. Split headers from body at byte level
                    h_end = header_data.find(b"\r\n\r\n")
                    if h_end != -1:
                        header_block = header_data[:h_end]
                        body = header_data[h_end+4:]
                        
                        header_lines = header_block.split(b"\r\n")
                        if header_lines:
                            # 2. Rebuild headers: Keep first line, Filter existing auth, Inject ours
                            new_header_lines = [header_lines[0]]
                            
                            # Standard Proxy-Auth header to inject
                            auth_line = f"Proxy-Authorization: {self.auth_header}".encode()
                            new_header_lines.append(auth_line)
                            
                            # Filter out existing (client-side) auth headers
                            for line in header_lines[1:]:
                                if not line.lower().startswith(b"proxy-authorization:"):
                                    new_header_lines.append(line)
                            
                            # 3. Re-assemble with strict RFC CRLFs
                            header_data = b"\r\n".join(new_header_lines) + b"\r\n\r\n" + body
                except: pass

            target_writer.write(header_data)
            await target_writer.drain()

            async def pipe_upstream(r, w):
                try:
                    is_first = True
                    while True:
                        data = await r.read(16384)
                        if not data: break
                        
                        if is_first:
                            # If upstream returns 407, silently fail to prevent popup
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

            async def pipe_client(r, w):
                try:
                    while True:
                        data = await r.read(16383)
                        if not data: break
                        w.write(data)
                        await w.drain()
                except: pass
                finally:
                    try: w.close()
                    except: pass

            await asyncio.gather(
                pipe_client(reader, target_writer),
                pipe_upstream(target_reader, writer)
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
