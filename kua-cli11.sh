#!/bin/bash

for i in {1..20}; do
    /mini-ndn/kmn/kua/build/bin/kua-client put /ndn/cli1-site/cli1/b$i < /tmp/rand5m
done

for i in {1..100}; do
    /mini-ndn/kmn/kua/build/bin/kua-client put /ndn/cli1-site/cli1/c$i < /tmp/rand1m
done