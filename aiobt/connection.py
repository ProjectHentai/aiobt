import asyncio
from typing import Type, Tuple, Callable, Dict, Optional
from functools import partial
from collections import deque

from aiobt.abc import BaseConnection
from aiobt.protocol import BaseDHTProtocol
from aiobt.utils import decode_nodes, ensure_bytes
from aiobt.typing import IP


class DHTConnection(BaseConnection):
    def __init__(self, protocol_factory: Callable[[], BaseDHTProtocol],
                 nid: str,
                 loop: asyncio.AbstractEventLoop):
        super().__init__(protocol_factory, loop)
        self.nid = nid
        self._protocol = None

    async def listen(self, port: int = 6881):
        transport, protocol = await self._loop.create_datagram_endpoint(self._protocol_factory,
                                                                        local_addr=("0.0.0.0", port))
        self._protocol = protocol

    async def ping(self, addr: IP):
        return await self._protocol.ping(addr, nid=self.nid)

    async def find_node(self, addr: IP, target: Optional[str] = None):
        ret = await self._protocol.find_node(addr, target, self.nid)
        nodes: str = ret["r"]["nodes"]
        nodes = decode_nodes(ensure_bytes(nodes))
        ret["r"]["nodes"] = nodes
        return ret

    async def get_peers(self, addr: IP, info_hash: str):
        return await self._protocol.get_peers(addr, info_hash, self.nid)

    async def announce_peer(self, addr: IP, info_hash: str, port: int, token: str, implied_port: int = 1):
        """

        :param addr:
        :param info_hash:
        :param port:
        :param token:
        :param implied_port: 如果存在且未为零，则应忽略端口参数
        :return:
        """
        return await self._protocol.announce_peer(addr, info_hash, port, token, implied_port, self.nid)


class UTPConnection(BaseConnection):
    pass
