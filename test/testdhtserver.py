# dht server with auto send
import asyncio
from pprint import pprint
from functools import partial
import sys
import logging

logger = logging.getLogger("dhtprotocol")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

from aiobt import DummyDHTProtocol, decode_nodes, ensure_bytes, ensure_str, str_to_hex, entropy

BOOTSTRAP_NODES = (
    ("router.bittorrent.com", 6881),
    ("dht.transmissionbt.com", 6881),
    ("router.utorrent.com", 6881),
    ("router.bitcomet.com", 6881)
)


async def main():
    loop = asyncio.get_running_loop()
    # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    # sock.bind(("0.0.0.0", 6881))
    # sock.sendto(b"xxxxxx", ("dht.transmissionbt.com", 6881))
    transport, protocol = await loop.create_datagram_endpoint(partial(DummyDHTProtocol, 5, loop=loop),
                                                              local_addr=("0.0.0.0", 6881))
    print("dht server listening on 6881")
    # print(transport.get_extra_info("socket") is sock)
    for i in range(10):
        try:
            data = await protocol.ping(BOOTSTRAP_NODES[i % 4])
            pprint(data)
        except Exception as e:
            print(e)
            print("time out")


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # otherwise would could err
loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
