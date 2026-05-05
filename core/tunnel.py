import asyncio
import base64
import re

class ProxyTunnel:
    """Unlimited v6.6.4: Regex-based parsing for perfect accuracy with complex passwords."""
    
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
        self.upstream_addr = "Parsing..."
        self._parse_upstream(upstream_addr_raw)

    def _parse_upstream(self, s):
        try:
            if not s: return
            s = s.strip()
            
            # Pattern for host:port:user:pass
            # Matches: host (chars/digits/dots/hyphens), port (digits), user (any), pass (any)
            match = re.match(r'^([^:]+):(\d+):([^:]+):(.+)$', s)
            if match:
                self.upstream_host = match.group(1)
                self.upstream_port = int(match.group(2))
                user = match.group(3)
                pwd = match.group(4)
                auth = f"{user}:{pwd}"
                self.auth_header = f"Basic {base64.b64encode(auth.encode()).decode()}"
                self.upstream_addr = f"{self.upstream_host}:{self.upstream_port}"
                return

            # Fallback for user:pass@host:port
            match = re.match(r'^([^:]+):([^@]+)@([^:]+):(\d+)$', s)
            if match:
                user = match.group(1)
                pwd = match.group(2)
                self.upstream_host = match.group(3)
                self.upstream_port = int(match.group(4))
                auth = f"{user}:{pwd}"
                self.auth_header = f"Basic {base64.b64encode(auth.encode()).decode()}"
                self.upstream_addr = f"{self.upstream_host}:{self.upstream_port}"
                return
                
            # Final Fallback: host:port only
            parts = s.split(":")
            if len(parts) == 2:
                self.upstream_host, self.upstream_port = parts[0], int(parts[1])
                self.upstream_addr = s
            else:
                self.upstream_addr = "Parse Error"
        except:
            self.upstream_addr = "Parse Error"

    async def _bridge(self, reader, writer):
        if not self.upstream_host: 
            writer.close()
            return
        target_writer = None
        try:
            self.connection_count += 1
            data = await asyncio.wait_for(reader.read(16384), timeout=10)
            if not data: return
            header_text = data.decode(errors='ignore')
            is_connect = header_text.startswith("CONNECT")
            try:
                target_reader, target_writer = await asyncio.wait_for(
                    asyncio.open_connection(self.upstream_host, self.upstream_port), 
                    timeout=15
                )
            except: return
            if is_connect:
                target = header_text.split("\r\n")[0].split(" ")[1]
                auth = f"Proxy-Authorization: {self.auth_header}\r\n" if self.auth_header else ""
                target_writer.write(f"CONNECT {target} HTTP/1.1\r\n{auth}Connection: keep-alive\r\n\r\n".encode())
                await target_writer.drain()
                resp = await asyncio.wait_for(target_reader.read(8192), timeout=10)
                if b"200" in resp.split(b"\r\n")[0]:
                    writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                    await writer.drain()
                else:
                    writer.close()
                    return
            else:
                if self.auth_header and "Proxy-Authorization" not in header_text:
                    idx = header_text.find("\r\n\r\n")
                    new_h = header_text[:idx] + f"\r\nProxy-Authorization: {self.auth_header}\r\n\r\n" + header_text[idx+4:] if idx != -1 else header_text
                    target_writer.write(new_h.encode())
                else: target_writer.write(data)
                await target_writer.drain()

            async def pipe(r, w):
                try:
                    while True:
                        c = await r.read(16384)
                        if not c: break
                        w.write(c)
                        await w.drain()
                except: pass
                finally:
                    try: w.close()
                    except: pass
            t1 = asyncio.create_task(pipe(reader, target_writer))
            t2 = asyncio.create_task(pipe(target_reader, writer))
            await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
            t1.cancel(); t2.cancel()
        except: pass
        finally:
            self.connection_count = max(0, self.connection_count - 1)
            try: writer.close()
            except: pass
            if target_writer:
                try: target_writer.close()
                except: pass

    async def start(self):
        if not self.upstream_host: return False
        try:
            self.server = await asyncio.start_server(self._bridge, '127.0.0.1', self.target_port)
            self.is_active = True
            return True
        except: return False

    async def stop(self):
        if self.server:
            self.is_active = False
            self.server.close()
            await self.server.wait_closed()
