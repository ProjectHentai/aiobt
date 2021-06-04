from aiobt.protocol import BaseDHTProtocol, DummyDHTProtocol
from aiobt.utils import decode_nodes, ensure_str, ensure_bytes, str_to_hex, entropy
from aiobt.connection import DHTConnection


# https://www.aneasystone.com/archives/2015/05/analyze-magnet-protocol-using-wireshark.html
# http://www.lyyyuna.com/2016/05/14/dht-sniffer/
# https://github.com/BrightStarry/zx-bt
# https://cnodejs.org/topic/57b5300de8db280a7c86515d
# https://www.jianshu.com/p/f1659aba5aed
# https://github.com/synodriver/simDownloader
# http://blog.chinaunix.net/uid-24399976-id-3060019.html
# http://blog.chinaunix.net/uid-14408083-id-2814554.html