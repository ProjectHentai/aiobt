# Peer Wire Protocol
import asyncio
from typing import Optional
from io import BytesIO

from pydantic import BaseModel, Field, validator
from typing import List
from typing_extensions import Literal

from aiobt.utils import ensure_str, ensure_bytes

DEFAULT_BUFFER_SIZE = 50


class PeerMessage(BaseModel):
    length: int  # 4 bytes
    message_id: Optional[int]  # 1 byte 后2个字段计入长度
    payload: bytes = Field(b"")

    @classmethod
    def keepalive(cls) -> "PeerMessage":
        return cls(length=0)

    @classmethod
    def choke(cls) -> "PeerMessage":
        return cls(length=1, message_id=0)

    @classmethod
    def unchoke(cls) -> "PeerMessage":
        return cls(length=1, message_id=1)

    @classmethod
    def interested(cls) -> "PeerMessage":
        return cls(length=1, message_id=2)  # todo 完成

    @classmethod
    def not_interested(cls) -> "PeerMessage":
        return cls(length=1, message_id=3)


class PeerMessagePacket(BaseModel):
    messages: List[PeerMessage]

    @classmethod
    def from_bytes(cls):
        pass  # todo

    def to_bytes(self) -> bytes:
        pass


class PeerHandshakePacket(BaseModel):
    pstrlen: int = Field(19)
    pstr: Literal["BitTorrent protocol"] = Field("BitTorrent protocol")
    reserved: bytes = Field(bytes(8))
    info_hash: bytes
    peer_id: bytes

    @validator("reserved")
    def check_reserved(cls, v):
        if len(v) != 8:
            raise ValueError("reserved field must len 8")
        return v

    @validator("info_hash")
    def check_info_hash(cls, v):
        if len(v) != 20:
            raise ValueError("info_hash field must len 20")
        return v

    @validator("peer_id")
    def check_peer_id(cls, v):
        if len(v) != 20:
            raise ValueError("peer_id field must len 20")
        return v

    @classmethod
    def from_bytes(cls, data: bytes) -> "PeerHandshakePacket":
        return cls.from_reader(data)

    @classmethod
    def from_reader(cls, reader: BytesIO) -> "PeerHandshakePacket":
        pstrlen = int.from_bytes(reader.read(1), "big")
        pstr = ensure_str(reader.read(pstrlen))
        reserved = reader.read(8)
        info_hash = reader.read(20)
        peer_id = reader.read(20)
        return cls(pstrlen=pstrlen, pstr=pstr, reserved=reserved, info_hash=info_hash, peer_id=peer_id)

    def to_bytes(self) -> bytes:
        writer = BytesIO()
        writer.write(self.pstrlen.to_bytes(1, "big"))
        writer.write(ensure_bytes(self.pstr))
        writer.write(self.reserved)
        writer.write(self.info_hash)
        writer.write(self.peer_id)
        return writer.getvalue()


class BaseTCPPeerServerProtocol(asyncio.BufferedProtocol):
    def __init__(self):
        pass


class BaseTCPPeerClientProtocol(asyncio.BufferedProtocol):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop or asyncio.get_event_loop()
        self.transport = None
        self._close_waiter = self._loop.create_future()
        self._buffer: bytearray = None

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc:
            self._close_waiter.set_exception(exc)
        else:
            self._close_waiter.set_result(None)

    def get_buffer(self, sizehint: int):
        if sizehint == -1:
            self._buffer = bytearray(DEFAULT_BUFFER_SIZE)
        self._buffer = bytearray(sizehint)
        return self._buffer

    def buffer_updated(self, nbytes: int) -> None:
        """data_received"""
        data: bytearray = self._buffer[:nbytes]  # todo

    def eof_received(self):
        return None

    async def close(self):
        self.transport.close()
        await self._close_waiter

    @property
    def closed(self):
        return self._close_waiter.done()

    async def hand_shake(self):
        """client发送握手"""
        pass


class BaseUDPPeerProtocol(asyncio.DatagramProtocol):
    pass
