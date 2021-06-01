from hashlib import sha1
from random import randint
from socket import inet_ntoa
from struct import unpack
from typing import Union, List, Tuple

# from pydantic.dataclasses import dataclass
from enum import IntEnum


def entropy(length: int) -> str:
    """
    产生给定长度的随机字符串
    :param length:
    :return:
    """
    return "".join(chr(randint(0, 255)) for _ in range(length))


def random_id() -> bytes:
    """
    产生160位的bytes 20字节
    :return:
    """
    h = sha1()
    h.update(entropy(20).encode())
    return h.digest()


def decode_nodes(nodes: bytes) -> List[Tuple]:
    n: List[Tuple] = []
    length = len(nodes)
    if (length % 26) != 0:
        return n

    for i in range(0, length, 26):
        nid = nodes[i:i + 20]
        ip = inet_ntoa(nodes[i + 20:i + 24])
        port = unpack("!H", nodes[i + 24:i + 26])[0]
        n.append((nid, ip, port))

    return n


def get_neighbor(target, nid, end=10) -> str:
    return target[:end] + nid[end:]


def str_to_hex(x: str) -> str:
    return "".join(map(lambda x: hex(ord(x))[2:], x))


def str_to_bytes(x: str) -> bytes:
    return bytes(ord(c) for c in x)


def bytes_to_str(x: bytes) -> str:
    return "".join(map(lambda c: chr(c), x))


def ensure_str(x: Union[str, bytes]) -> str:
    if isinstance(x, str):
        return x
    return bytes_to_str(x)


def ensure_bytes(x: Union[str, bytes]) -> bytes:
    if isinstance(x, str):
        return str_to_bytes(x)
    return x
