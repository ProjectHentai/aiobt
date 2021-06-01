from abc import ABC
from functools import partial
from typing import Type, Callable
import asyncio


class BaseConnection(ABC):

    def __init__(self, protocol_factory: Callable[[], asyncio.BaseProtocol],
                 loop: asyncio.AbstractEventLoop):
        """maybe tcp connection"""
        self._protocol_factory = protocol_factory
        self._loop = loop

    @property
    def closed(self):
        return self._protocol.closed

    async def close(self):
        await self._protocol.close()
