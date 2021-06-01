import asyncio
from asyncio import DatagramTransport
from typing import Optional, Tuple, Dict
from collections import deque
import logging

from bencode import bencode, bdecode

from aiobt.utils import random_id, get_neighbor, entropy, decode_nodes, ensure_bytes, ensure_str
from aiobt.typing import RequestHandler, IP

logger = logging.getLogger("dhtprotocol")

TID_LENGTH = 2
RE_JOIN_DHT_INTERVAL = 3
MONITOR_INTERVAL = 10
TOKEN_LENGTH = 8  # get peer的token


class KNode:

    def __init__(self, nid: str, ip: str, port: int):
        self.nid = nid
        self.ip = ip
        self.port = port


class BaseDHTProtocol(asyncio.DatagramProtocol):
    """DHT协议实现"""
    _waiters: Dict[str, asyncio.Future]
    _close_waiter: asyncio.Future
    process_request_actions = Dict[str, RequestHandler]

    def __init__(self, timeout=5,
                 nid: Optional[str] = None,
                 loop: Optional[asyncio.AbstractEventLoop] = None):
        """仍一些future封装一下 建立一个链接多一个protocol实例"""
        self.process_request_actions = {
            "get_peers": self.on_get_peers_request,
            "announce_peer": self.on_announce_peer_request,
            "find_node": self.on_find_node_request,
            "ping": self.on_ping_request
        }
        self.timeout = timeout
        self.nid = nid or entropy(20)  # nodeid
        self._loop = loop or asyncio.get_event_loop()
        self._waiters = {}
        self._close_waiter = self._loop.create_future()

    def connection_made(self, transport: DatagramTransport) -> None:
        """有不明真相的Node前来问路"""
        self.transport = transport
        # self.transport.sendto()  # todo 开始问路

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """transport.abort() close()"""
        if exc:
            self._close_waiter.set_exception(exc)
        else:
            self._close_waiter.set_result(None)

    def datagram_received(self, data: bytes, addr: IP):
        data = bdecode(ensure_str(data))
        try:
            if data["y"] in ("r", "e"):  # response error  其他节点的返回值
                tid = data["t"]
                self._waiters[tid].set_result(data)
            elif data["y"] == "q":  # 我被当成了服务器
                # 这时候我什么都不说 闷声发大财 这是坠吼的
                ret = self.process_request_actions[data["q"]](data, addr)
                if asyncio.iscoroutine(ret):
                    self._loop.create_task(ret)
        except:
            tid = entropy(TID_LENGTH)
            msg = {
                "t": tid,
                "y": "e",
                "e": [202, "Server Error"]
            }
            self.transport.sendto(ensure_bytes(bencode(msg)), addr)

    def error_received(self, exc: Optional[Exception]):
        logger.error(str(exc))

    async def send_request(self, msg: dict, addr: Optional[IP] = None) -> dict:
        tid = msg["t"]
        assert tid not in self._waiters
        try:
            future = self._loop.create_future()
            self._waiters[tid] = future
            self.transport.sendto(ensure_bytes(bencode(msg)), addr)
            # self.transport.get_extra_info("socket").sendto(ensure_bytes(bencode(msg)), addr)
            return await asyncio.wait_for(future, self.timeout)
        finally:
            del self._waiters[tid]

    async def krpc(self, addr: IP, t: str, y: str, q: str, a):
        msg = {
            "t": t,
            "y": y,
            "q": q,
            "a": a
        }  # todo  还有个v : version 也是str
        return await self.send_request(msg, addr)

    async def ping(self, addr: Optional[IP] = None, nid: Optional[str] = None):
        tid = entropy(TID_LENGTH)
        nid = nid if nid else self.nid
        return await self.krpc(addr, tid, "q", "ping", {"id": nid})

    async def find_node(self, addr: IP, target: Optional[str] = None, nid: Optional[str] = None):
        """
        第一个必填关键字是 t，这是一个字符串表示的 transaction ID。它由请求 node 产生，且包含在回复中，
        所以回复有可能对应单个 node 的多个请求。transaction ID 应该被编码成字符串表示的二进制数字，通常是两个字符，
        这样就能包含 2^16 种请求。另一个必填关键字是 y，其对应值表示消息类型，为 q, r 或 e。
        :param target: TARGET NDOE
        :param addr:
        :param nid: self nodeid
        :return:
        """
        nid = get_neighbor(nid, self.nid) if nid else self.nid
        tid = entropy(TID_LENGTH)
        return await self.krpc(addr, tid, "q", "find_node", {
            "id": nid,
            "target": target or self.nid
        })

    async def get_peers(self, addr: IP, info_hash: str, nid: Optional[str] = None):
        """
        {"t":"aa", "y":"q", "q":"get_peers", "a": {"id":"abcdefghij0123456789", "info_hash":"mnopqrstuvwxyz123456"}}
        :param info_hash:
        :param addr:
        :param nid:
        :return:
        """
        nid = nid if nid else self.nid
        tid = entropy(TID_LENGTH)
        return await self.krpc(addr, tid, "q", "get_peers", {
            "id": nid,
            "info_hash": info_hash
        })

    async def announce_peer(self, addr: IP, info_hash: str, port: int, token: str, implied_port: int = 1,
                            nid: Optional[str] = None):
        """

        :param addr:
        :param info_hash:
        :param port:
        :param token:
        :param implied_port: 如果存在且未为零，则应忽略端口参数
        :param nid:
        :return:
        """
        nid = nid if nid else self.nid
        tid = entropy(TID_LENGTH)
        return await self.krpc(addr, tid, "q", "announce_peer", {
            "id": nid,
            "implied_port": implied_port,
            "info_hash": info_hash,
            "port": port,
            "token": token
        })

    def on_ping_request(self, data: dict, addr: IP):
        """
        {"t":"aa", "y":"q", "q":"ping", "a":{"id":"abcdefghij0123456789"}}
        {"t":"aa", "y":"r", "r": {"id":"mnopqrstuvwxyz123456"}}
        :param data:
        :param addr:
        :return:
        """
        raise NotImplementedError

    def on_get_peers_request(self, data: dict, addr: IP):
        """
        {"t":"aa", "y":"q", "q":"get_peers", "a": {"id":"abcdefghij0123456789", "info_hash":"mnopqrstuvwxyz123456"}}

        Response with peers = {"t":"aa", "y":"r", "r": {"id":"abcdefghij0123456789", "token":"aoeusnth", "values": ["axje.u", "idhtnm"]}}
        Response with closest nodes = {"t":"aa", "y":"r", "r": {"id":"abcdefghij0123456789", "token":"aoeusnth", "nodes": "def456..."}}
        :param data:
        :param addr:
        :return:
        """
        raise NotImplementedError

    def on_announce_peer_request(self, data: dict, addr: IP):
        """
        {"t":"aa", "y":"q", "q":"announce_peer", "a": {"id":"abcdefghij0123456789", "implied_port": 1, "info_hash":"mnopqrstuvwxyz123456", "port": 6881, "token": "aoeusnth"}

        {"t":"aa", "y":"r", "r": {"id":"mnopqrstuvwxyz123456"}}
        :param data:
        :param addr:
        :return:
        """
        raise NotImplementedError

    def on_find_node_request(self, data: dict, addr: IP):
        raise NotImplementedError

    async def close(self):
        self.transport.close()
        await self._close_waiter

    @property
    def closed(self):
        return self._close_waiter.done()


class DummyDHTProtocol(BaseDHTProtocol):
    """Return no data dht node"""

    def __init__(self, timeout: float = 5,
                 nid: Optional[str] = None,
                 loop: Optional[asyncio.AbstractEventLoop] = None):
        """仍一些future封装一下 建立一个链接多一个protocol实例"""
        super().__init__(timeout, nid=nid, loop=loop)
        self.process_request_actions = {
            "get_peers": self.on_get_peers_request,
            "announce_peer": self.on_announce_peer_request,
            "find_node": self.on_find_node_request,
            "ping": self.on_ping_request
        }

    def on_ping_request(self, data: dict, addr: IP):
        """
        {"t":"aa", "y":"q", "q":"ping", "a":{"id":"abcdefghij0123456789"}}
        {"t":"aa", "y":"r", "r": {"id":"mnopqrstuvwxyz123456"}}
        :param data:
        :param addr:
        :return:
        """
        logger.debug(f"got ping request id:{data['a']['id']} addr:{addr}")
        ret = {
            "t": data["t"],
            "y": "r",
            "r": {"id": self.nid}
        }
        self.transport.sendto(ensure_bytes(bencode(ret)), addr)

    def on_get_peers_request(self, data: dict, addr: IP):
        """
        {"t":"aa", "y":"q", "q":"get_peers", "a": {"id":"abcdefghij0123456789", "info_hash":"mnopqrstuvwxyz123456"}}

        Response with peers = {"t":"aa", "y":"r", "r": {"id":"abcdefghij0123456789", "token":"aoeusnth", "values": ["axje.u", "idhtnm"]}}
        Response with closest nodes = {"t":"aa", "y":"r", "r": {"id":"abcdefghij0123456789", "token":"aoeusnth", "nodes": "def456..."}}
        :param data:
        :param addr:
        :return:
        """
        infohash: str = data["a"]["info_hash"]
        tid = data["t"]
        nid = data["a"]["id"]  # 对方 nodeid
        token = infohash[:TOKEN_LENGTH]
        logger.debug('get peers request: ' + infohash, addr[0], addr[1])
        ret = {
            "t": tid,
            "y": "r",
            "r": {
                "id": self.nid,
                "nodes": "",  # 臣妾找不到啊  可以和values同时返回
                "token": token
            }
        }
        self.transport.sendto(ensure_bytes(bencode(ret)), addr)

    def on_announce_peer_request(self, data: dict, addr: IP):
        """
        {"t":"aa", "y":"q", "q":"announce_peer", "a": {"id":"abcdefghij0123456789", "implied_port": 1, "info_hash":"mnopqrstuvwxyz123456", "port": 6881, "token": "aoeusnth"}

        {"t":"aa", "y":"r", "r": {"id":"mnopqrstuvwxyz123456"}}
        :param data:
        :param addr:
        :return:
        """
        infohash = data["a"]["info_hash"]
        token = data["a"]["token"]
        nid = data["a"]["id"]
        tid = data["t"]
        logger.debug(f"announce peer request infohash:{infohash} token:{token}")

        if infohash[:TOKEN_LENGTH] == token:
            if "implied_port" in data["a"] and data["a"]["implied_port"] != 0:
                port = addr[1]
            else:
                port = data["a"]["port"]
                if port < 1 or port > 65535:
                    return
        ret = {
            "t": tid,
            "y": "r",
            "r": {"id": self.nid}
        }
        self.transport.sendto(ensure_bytes(bencode(ret)), addr)

    def on_find_node_request(self, data: dict, addr: IP):
        pass
