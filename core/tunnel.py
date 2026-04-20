import asyncio
import base64
import socket

class ProxyTunnel:
    """Universal Pipe v6.2.1: Robust multi-format parsing (supports user:pass@host:port)."""
    
    def __init__(self, id, target_port, upstream_addr_raw):
        self.id = id
        self.target_port = target_port
        self.upstream_addr_raw = upstream_addr_raw
        self.is_active = False
        self.auth_header = None
        self.connection_count = 0
        self.server = None
        
        self.upstream_host = None
        self.upstream_port = None
        self._parse_upstream(upstream_addr_raw)

    def _parse_upstream(self, s):
        """Robustly extracts host, port and credentials from multiple formats."""
        try:
            s = s.strip()
            display_str = s
            
            if "@" in s:
                # Format: user:pass@host:port
                auth_part, addr_part = s.rsplit("@", 1)
                self.upstream_host, self.upstream_port = addr_part.rsplit(":", 1)
                self.upstream_port = int(self.upstream_port)
                self.auth_header = f"Basic {base64.b64encode(auth_part.encode()).decode()}"
                display_str = addr_part
            else:
                parts = s.split(":")
                if len(parts) >= 4:
                    # Format: host:port:user:pass
                    self.upstream_host = parts[0]
                    self.upstream_port = int(parts[1])
                    auth = f"{parts[2]}:{parts[3]}"
                    self.auth_header = f"Basic {base64.b64encode(auth.encode()).decode()}"
                    display_str = f"{parts[0]}:{parts[1]}"
                elif len(parts) == 2:
                    # Format: host:port (No auth)
                    self.upstream_host = parts[0]
                    self.upstream_port = int(parts[1])
                    display_str = s
            
            # Truncate for UI
            self.upstream_addr = display_str if len(display_str) <= 30 else display_str[:27] + "..."
        except Exception:
            self.upstream_addr = "Parse Error"

    def update_upstream(self, new_upstream):
        """Updates the upstream target for the next new connection."""
        self._parse_upstream(new_upstream)

    async def _bridge(self, reader, writer):
        """Dual-Mode Handshaking (CONNECT vs Header Injection)."""
        target_writer = None
        try:
            self.connection_count += 1
            
            data = await reader.read(8192)
            if not data: return
            
            header_text = data.decode(errors='ignore')
            lines = header_text.split("\r\n")
            if not lines: return
            
            first_line = lines[0]
            is_connect = first_line.startswith("CONNECT")
            
            target_reader, target_writer = await asyncio.open_connection(
                self.upstream_host, int(self.upstream_port)
            )
            
            if is_connect:
                target = first_line.split(" ")[1]
                auth_line = f"Proxy-Authorization: {self.auth_header}\r\n" if self.auth_header else ""
                handshake = f"CONNECT {target} HTTP/1.1\r\n{auth_line}Connection: keep-alive\r\n\r\n"
                target_writer.write(handshake.encode())
                await target_writer.drain()
                
                resp = await target_reader.read(4096)
                if b"200" in resp.split(b"\r\n")[0]:
                    writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                    await writer.drain()
                else:
                    writer.close()
                    return
            else:
                # HTTP Mode: Inject auth header
                if self.auth_header and "Proxy-Authorization" not in header_text:
                    insertion_point = header_text.find("\r\n")
                    if insertion_point != -1:
                        new_header = (
                            header_text[:insertion_point + 2] + 
                            f"Proxy-Authorization: {self.auth_header}\r\n" + 
                            header_text[insertion_point + 2:]
                        )
                        target_writer.write(new_header.encode())
                    else:
                        target_writer.write(data)
                else:
                    target_writer.write(data)
                await target_writer.drain()

            async def pipe(r, w):
                try:
                    while True:
                        chunk = await r.read(16384)
                        if not chunk: break
                        w.write(chunk)
                        await w.drain()
                except: pass
                finally:
                    try: w.close()
                    except: pass

            await asyncio.gather(pipe(reader, target_writer), pipe(target_reader, writer))

        except Exception:
            pass
        finally:
            self.connection_count = max(0, self.connection_count - 1)
            try: writer.close()
            except: pass
            if target_writer:
                try: target_writer.close()
                except: pass

    async def start(self):
        """Starts the gateway server."""
        try:
            self.server = await asyncio.start_server(self._bridge, '127.0.0.1', self.target_port)
            self.is_active = True
            return True
        except:
            return False

    async def stop(self):
        """Gracefully stops the gateway server."""
        if self.server:
            self.is_active = False
            self.server.close()
            await self.server.wait_closed()
