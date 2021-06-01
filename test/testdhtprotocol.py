# -*- coding: utf-8 -*-
import asyncio
from functools import partial


from aiobt import DummyDHTProtocol, decode_nodes, ensure_bytes, ensure_str, str_to_hex, entropy

BOOTSTRAP_NODES = (
    ("router.bittorrent.com", 6881),
    ("dht.transmissionbt.com", 6881),
    ("router.utorrent.com", 6881),
    ("router.bitcomet.com", 6881)
)


async def main():
    loop = asyncio.get_event_loop()
    transport, protocol = await loop.create_datagram_endpoint(partial(DummyDHTProtocol, 2, loop=loop),
                                                              remote_addr=BOOTSTRAP_NODES[1]
                                                              )
    while True:
        try:
            data = await protocol.find_node(None, entropy(20), protocol.nid)
            nodes = decode_nodes(ensure_bytes(data["r"]["nodes"]))
            for node in nodes:
                print(node[0].hex(), node[1], node[2])
        except asyncio.TimeoutError:
            print("超时重试")
            continue
    # await asyncio.gather(*tasks)


asyncio.run(main())
