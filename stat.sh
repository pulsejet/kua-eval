#!/bin/bash
for var in "$@"
do
    cat /sys/class/net/$var/statistics/rx_packets
    cat /sys/class/net/$var/statistics/tx_packets
    cat /sys/class/net/$var/statistics/rx_bytes
    cat /sys/class/net/$var/statistics/tx_bytes
done