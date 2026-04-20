import asyncio
import base64

class ProxyTunnel:
    """Manages a single tunnel with aggressive RFC-compliant authentication handling."""
    
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
            # Read enough to get full headers
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

            # Aggressive RFC Injection
            if self.auth_header:
                try:
                    # Split into headers and body
                    parts = header_data.split(b"\r\n\r\n", 1)
                    header_block = parts[0].decode(errors='ignore')
                    body = parts[1] if len(parts) > 1 else b""
                    
                    lines = header_block.split("\r\n")
                    if lines:
                        # 1. Clear existing auth headers
                        new_lines = [lines[0]] # Keep request line
                        for line in lines[1:]:
                            if not line.lower().startswith("proxy-authorization:"):
                                new_lines.append(line)
                        
                        # 2. Add our correct auth header and connection quality header
                        new_lines.insert(1, f"Proxy-Authorization: {self.auth_header}")
                        new_lines.insert(2, "Proxy-Connection: Keep-Alive")
                        
                        # 3. Assemble back with strict CRLF
                        header_data = "\r\n".join(new_lines).encode() + b"\r\n\r\n" + body
                except:
                    pass # Fallback to original if processing fails

            target_writer.write(header_data)
            await target_writer.drain()

            async def pipe_upstream_to_client(r, w):
                try:
                    first_packet = True
                    while True:
                        data = await r.read(16384)
                        if not data: break
                        
                        if first_packet:
                            if b"HTTP/1.1 407" in data or b"HTTP/1.0 407" in data:
                                self.status = "[bold red]AUTH FAIL (407)[/]"
                                break
                            first_packet = False
                            self.status = "[green]ACTIVE[/]"
                            
                        w.write(data)
                        await w.drain()
                except: pass
                finally:
                    try: w.close()
                    except: pass

            async def pipe_client_to_upstream(r, w):
                try:
                    while True:
                        data = await r.read(16384)
                        if not data: break
                        w.write(data)
                        await w.drain()
                except: pass
                finally:
                    try: w.close()
                    except: pass

            await asyncio.gather(
                pipe_client_to_upstream(reader, target_writer),
                pipe_upstream_to_client(target_reader, writer)
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
