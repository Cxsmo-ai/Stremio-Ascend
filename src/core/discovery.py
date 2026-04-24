import asyncio
import logging
import socket
from typing import List, Optional

logger = logging.getLogger("stremio-rpc")

class ADBDiscovery:
    def __init__(self, port: int = 5555):
        self.port = port

    async def scan_network(self) -> List[str]:
        local_ip = self._get_local_ip()
        if not local_ip:
            return []

        subnet = ".".join(local_ip.split(".")[:3])
        tasks = []

        # Scan 1-254
        for i in range(1, 255):
            ip = f"{subnet}.{i}"
            tasks.append(self._check_port(ip, self.port))

        results = await asyncio.gather(*tasks)
        return [ip for ip in results if ip]

    def _get_local_ip(self) -> Optional[str]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return None

    async def _check_port(self, ip: str, port: int) -> Optional[str]:
        conn = asyncio.open_connection(ip, port)
        try:
            reader, writer = await asyncio.wait_for(conn, timeout=0.2)
            writer.close()
            await writer.wait_closed()
            return ip
        except:
            return None
