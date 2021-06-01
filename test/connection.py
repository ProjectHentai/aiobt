import asyncio
import sys
from pprint import pprint

from aiobt import DHTConnection, DummyDHTProtocol, entropy

BOOTSTRAP_NODES = (
    ("router.bittorrent.com", 6881),
    ("dht.transmissionbt.com", 6881),
    ("router.utorrent.com", 6881),
    ("router.bitcomet.com", 6881)

)


async def main():
    loop = asyncio.get_running_loop()
    client = DHTConnection(lambda: DummyDHTProtocol(5, loop=loop), entropy(20), loop)
    await client.listen()
    for i in range(4):
        try:
            pprint(f"ping {BOOTSTRAP_NODES[i % 4]}")
            data = await client.ping(BOOTSTRAP_NODES[i % 4])
            pprint(data)
            i += 1
        except Exception as e:
            print(e)
            i += 1
            continue
    data = await client.find_node(("router.utorrent.com", 6881), entropy(20))
    pprint(data)
    # await asyncio.sleep(3600)


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # otherwise would could err
loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
