#!/bin/bash

pkill redis-server
pkill nfd
pkill nlsr
pkill kua
pkill kua-master
pkill kua-client

rm -f results.csv
rm -rf /tmp/minindn/
python3 eval.py dc.conf