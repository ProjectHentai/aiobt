# [DHT协议](http://www.bittorrent.org/beps/bep_0005.html)

http://www.lyyyuna.com/2016/03/26/dht01/

有一个名为implied\u port的可选参数，其值为0或1。如果该参数存在且不为零，则应忽略port参数，而应将UDP数据包的源端口用作对等方的端口。这对于NAT后面可能不知道其外部端口的对等方很有用，并且支持uTP，它们在与DHT端口相同的端口上接受传入连接。