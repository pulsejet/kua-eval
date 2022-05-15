import time
import redis
import sys

r = redis.RedisCluster(host=sys.argv[1], port=6379)

def readf(id, count):
    for i in range(count):
        res = r.get(id + str(i+1))
        print(id + str(i+1), 'read')


readf('b', 20)
time.sleep(2)
readf('c', 100)
time.sleep(2)
