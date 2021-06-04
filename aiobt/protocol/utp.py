import asyncio
from asyncio import DatagramTransport
from typing import List, Optional, DefaultDict
from collections import defaultdict
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

    def to_bytes(self) -> bytes:
        writer = BytesIO()
        writer.write(self.extension_flag.to_bytes(1, "big"))
        writer.write(self.len.to_bytes(1, "big"))
        writer.write(self.payload)
        return writer.getvalue()


class UTPPacket(BaseModel):
    type: UTPType  # 4
    ver: int  # 4
    extension_flag: int  # 8
    connection_id: int  # 16
    timestamp_microseconds: int  # 32
    timestamp_difference_microseconds: int  # 32
    wnd_size: int  # 32
    seq_nr: int  # 16
    ack_nr: int  # 16
    extensions: List[Extension] = Field(default_factory=list)
    payload: bytes = Field(b"")

    @classmethod
    def from_bytes(cls, data: bytes) -> "UTPPacket":
        return cls.from_reader(BytesIO(data))

    @classmethod
    def from_reader(cls, reader: BytesIO) -> "UTPPacket":
        temp: int = int.from_bytes(reader.read(1), "big")
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
        payload = reader.read()
        return cls(type=type_,
                   ver=ver,
                   extension_flag=extension_flag,
                   connection_id=connection_id,
                   timestamp_microseconds=timestamp_microseconds,
                   timestamp_difference_microseconds=timestamp_difference_microseconds,
                   wnd_size=wnd_size,
                   seq_nr=seq_nr,
                   ack_nr=ack_nr,
                   extensions=extensions,
                   payload=payload)

    def to_bytes(self):
        writer = BytesIO()
        writer.write((self.type << 4 | self.ver).to_bytes(1, "big"))
        writer.write(self.extension_flag.to_bytes(1, "big"))
        writer.write(self.connection_id.to_bytes(2, "big"))
        writer.write(self.timestamp_microseconds.to_bytes(4, "big"))
        writer.write(self.timestamp_difference_microseconds.to_bytes(4, "big"))
        writer.write(self.wnd_size.to_bytes(4, "big"))
        writer.write(self.seq_nr.to_bytes(2, "big"))
        writer.write(self.ack_nr.to_bytes(2, "big"))
        for extension in self.extensions:
            writer.write(extension.to_bytes())
        writer.write(self.payload)
        return writer.getvalue()


class BaseUTPProtocol(asyncio.DatagramProtocol):
    def __init__(self, buffer_size: int, timeout: float = 5, loop: asyncio.AbstractEventLoop = None):
        self.buffer_size = buffer_size
        self.timeout = timeout
        self._loop = loop or asyncio.get_event_loop()
        self._buffer: DefaultDict[IP, asyncio.Queue] = defaultdict(
            lambda: asyncio.Queue(self.buffer_size))  # todo 需要修改 改成流？
        self._close_waiter = self._loop.create_future()
        self.transport: DatagramTransport = None  # type: ignore

    def datagram_received(self, data: bytes, addr: IP) -> None:
        """分包"""
        packet = UTPPacket.from_bytes(data)
        self._buffer[addr].put_nowait(packet)

    def connection_made(self, transport: DatagramTransport) -> None:  # type: ignore
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

    async def search_buffer(self, addr: IP, connection_id: int) -> "UTPPacket":
        """从buffer查找属于自己这个connection的包"""
        while True:
            pkt: UTPPacket = await self._buffer[addr].get()
            if pkt.connection_id == connection_id:
                return pkt
            await self._buffer[addr].put(pkt)
            await asyncio.sleep(0)  # no blocking

    async def send_packet(self,
                          addr: IP,
                          type: int,
                          ver: int,
                          extension_flag: int,
                          connection_id: int,
                          timestamp_microseconds: int,
                          timestamp_difference_microseconds: int,
                          wnd_size: int,
                          seq_nr: int,
                          ack_nr: int,
                          extensions: List[Extension] = None):
        msg = UTPPacket(type=type,
                        ver=ver,
                        extension_flag=extension_flag,
                        connection_id=connection_id,
                        timestamp_microseconds=timestamp_microseconds,
                        timestamp_difference_microseconds=timestamp_difference_microseconds,
                        wnd_size=wnd_size,
                        seq_nr=seq_nr,
                        ack_nr=ack_nr,
                        extensions=extensions or [])
        self.transport.sendto(msg.to_bytes(), addr)
        pkt: UTPPacket = await asyncio.wait_for(self.search_buffer(addr, connection_id), self.timeout)
        return pkt
