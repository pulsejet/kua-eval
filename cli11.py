import time
import redis
import sys

r = redis.RedisCluster(host=sys.argv[1], port=6379)


def writef(file, id, count):
    with open(file, 'rb') as f:
        bs = f.read()
        for i in range(count):
            r.set(id + str(i+1), bs)
            print(file, id + str(i+1), 'written')


writef('/tmp/rand5m', 'b', 20)
time.sleep(2)
writef('/tmp/rand1m', 'c', 100)
# time.sleep(2)
# writef('/tmp/rand100k', 'd', 1000)
# time.sleep(2)
# writef('/tmp/rand10k', 'e', 10000)
