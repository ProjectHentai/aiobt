import asyncio
from asyncio import DatagramTransport


class UTPType(IntEnum):
    ST_DATA = 0
    ST_FIN = 1
    ST_STATE = 2
    ST_RESET = 3
    ST_SYN = 4


class UTPPacket:
    type_: UTPType  # 4
    ver: int  # 4
    extension: int  # 8
    connection_id: int  # 8
    timestamp_microseconds: int
    timestamp_difference_microseconds: int
    wnd_size: int


class BaseUTPProtocol(asyncio.DatagramProtocol):
    pass
