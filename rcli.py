import redis
import sys

r = redis.RedisCluster(host=sys.argv[1], port=6379)


def writef(file, id, count):
    with open(file, 'rb') as f:
        for i in range(count):
            r.set(id + str(i+1), f.read())
            print(file, id + str(i+1), 'written')


writef('/tmp/rand5m', 'b', 20)
writef('/tmp/rand1m', 'c', 100)
