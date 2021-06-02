import asyncio
from asyncio import DatagramTransport
from typing import List, Optional
from enum import IntEnum
from io import BytesIO

from pydantic import BaseModel, Field

from aiobt.typing import IP


class UTPType(IntEnum):
    ST_DATA = 0
    ST_FIN = 1
    ST_STATE = 2
    ST_RESET = 3
    ST_SYN = 4


class Extension(BaseModel):
    extension_flag: int
    len: int
    payload: bytes = Field(b"")

    @classmethod
    def from_bytes(cls, data: bytes) -> "Extension":
        return cls.from_reader(BytesIO(data))

    @classmethod
    def from_reader(cls, reader: BytesIO) -> "Extension":
        extension_flag = int.from_bytes(reader.read(1), "big")
        len_ = int.from_bytes(reader.read(1), "big")
        payload: bytes = reader.read(len_)
        return cls(extension_flag=extension_flag, len=len_, payload=payload)


class UTPPacket(BaseModel):
    type_: UTPType  # 4
    ver: int  # 4
    extension_flag: int  # 8
    connection_id: int  # 16
    timestamp_microseconds: int  # 32
    timestamp_difference_microseconds: int  # 32
    wnd_size: int  # 32
    seq_nr: int  # 16
    ack_nr: int  # 16
    extensions: List[Extension]

    @classmethod
    def from_bytes(cls, data: bytes) -> "UTPPacket":
        return cls.from_reader(BytesIO(data))

    @classmethod
    def from_reader(cls, reader: BytesIO) -> "UTPPacket":
        temp: int = int.from_bytes(reader.read(4), "big")
        type_ = (temp & 0xF0) >> 4
        ver = (temp & 0x0F)
        extension_flag = int.from_bytes(reader.read(1), "big")
        connection_id = int.from_bytes(reader.read(2), "big")
        timestamp_microseconds = int.from_bytes(reader.read(4), "big")
        timestamp_difference_microseconds = int.from_bytes(reader.read(4), "big")
        wnd_size = int.from_bytes(reader.read(4), "big")
        seq_nr = int.from_bytes(reader.read(2), "big")
        ack_nr = int.from_bytes(reader.read(2), "big")
        extensions = []
        if extension_flag:
            while True:
                extension = Extension.from_reader(reader)
                extensions.append(extension)
                if not extension.extension_flag:
                    break
        return cls(type_=type_,
                   ver=ver,
                   extension_flag=extension_flag,
                   connection_id=connection_id,
                   timestamp_microseconds=timestamp_microseconds,
                   timestamp_difference_microseconds=timestamp_difference_microseconds,
                   wnd_size=wnd_size,
                   seq_nr=seq_nr,
                   ack_nr=ack_nr,
                   extensions=extensions)


class BaseUTPProtocol(asyncio.DatagramProtocol):
    def __init__(self, buffer_size: int, loop: asyncio.AbstractEventLoop):
        self.buffer_size = buffer_size
        self._loop = loop
        self._buffer = asyncio.Queue(self.buffer_size)
        self._close_waiter = self._loop.create_future()

    def datagram_received(self, data: bytes, addr: IP) -> None:
        """分包"""
        packet = UTPPacket.from_bytes(data)
        self._buffer.put_nowait((packet, addr))

    def connection_made(self, transport: DatagramTransport) -> None:
        self.transport = transport

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """"""
        if exc:
            self._close_waiter.set_exception(exc)
        else:
            self._close_waiter.set_result(None)

    def error_received(self, exc: Exception) -> None:
        pass

    async def close(self):
        self.transport.close()
        await self._close_waiter

    @property
    def closed(self):
        return self._close_waiter.done()

    def send_request(self, msg, addr: IP):
        self.transport.sendto(msg, addr)
