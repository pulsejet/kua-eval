# -*- Mode:python; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2015-2020, The University of Memphis,
#                          Arizona Board of Regents,
#                          Regents of the University of California.
#
# This file is part of Mini-NDN.
# See AUTHORS.md for a complete list of Mini-NDN authors and contributors.
#
# Mini-NDN is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mini-NDN is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mini-NDN, e.g., in COPYING.md file.
# If not, see <http://www.gnu.org/licenses/>.

from time import sleep, time_ns
from threading import Thread

from mininet.log import setLogLevel, info
from mininet.topo import Topo

from minindn.minindn import Minindn
from minindn.util import MiniNDNCLI
from minindn.apps.app_manager import AppManager
from minindn.apps.application import Application
from minindn.apps.nfd import Nfd
from minindn.helpers.ndn_routing_helper import NdnRoutingHelper
from minindn.helpers.ip_routing_helper import IPRoutingHelper

SERV_IP = ""


def collect_all_stats(id, net):
    rx_packets, tx_packets, rx_bytes, tx_bytes = 0, 0, 0, 0

    for node in net.hosts:
        rx_packets += int(node.cmd(
            "cat /sys/class/net/{}-eth0/statistics/rx_packets".format(node.name)).strip())
        tx_packets += int(node.cmd(
            "cat /sys/class/net/{}-eth0/statistics/tx_packets".format(node.name)).strip())
        rx_bytes += int(node.cmd(
            "cat /sys/class/net/{}-eth0/statistics/rx_bytes".format(node.name)).strip())
        tx_bytes += int(node.cmd(
            "cat /sys/class/net/{}-eth0/statistics/tx_bytes".format(node.name)).strip())

    node.cmd("echo '{} {} {} {} {} {}' >> /mini-ndn/kmn/results.csv".format(
             id, time_ns(), rx_packets, tx_packets, rx_bytes, tx_bytes))


class Redis(Application):
    def __init__(self, node):
        Application.__init__(self, node)
        self.confFile = '{}/redis.conf'.format(self.homeDir)
        self.logFile = 'redis.log'

        with open(self.confFile, 'w') as f:
            f.write("""
port 6379
protected-mode no
cluster-enabled yes
cluster-config-file nodes.conf
cluster-node-timeout 5000
appendonly yes
""")

    def start(self):
        Application.start(
            self, 'redis-server {}'.format(self.confFile), logfile=self.logFile)


class Cli11(Application):
    def start(self):
        Application.start(
            self, 'python3 /mini-ndn/kmn/rcli.py {}'.format(SERV_IP), logfile='cli11.log')


if __name__ == '__main__':
    setLogLevel('info')

    Minindn.cleanUp()
    Minindn.verifyDependencies()

    ndn = Minindn()

    ndn.start()

    # Calculate all routes for IP routing
    IPRoutingHelper.calcAllRoutes(ndn.net)
    info("IP routes configured\n")

    info('Starting redis\n')
    storageNodes = [h for h in ndn.net.hosts if h.name[0] == 'r']
    redis = AppManager(ndn, storageNodes, Redis)

    sleep(1)

    info('Starting redis cluster\n')
    clusternode = storageNodes[0]
    hostlist = ""
    for h in storageNodes:
        hostlist += h.IP() + ':6379 '
    cmd = 'redis-cli --cluster create --cluster-yes --cluster-replicas 1 {}'.format(
        hostlist)
    info(clusternode.cmd(cmd))
    sleep(1)

    # Get client nodes
    cli1 = ndn.net.get('cli1')
    cli2 = ndn.net.get('cli2')
    cli3 = ndn.net.get('cli3')
    cip = clusternode.IP()

    # Collect stats
    collect_all_stats(0, ndn.net)

    SERV_IP = cip

    # Start first client
    cli11 = AppManager(ndn, [cli1], Cli11)

    # Collect stats
    t = 0.1
    total_time = 10
    for i in range(int(total_time/t)):
        collect_all_stats(round((i+1)*t, 1), ndn.net)
        sleep(t)

    #info('Starting NFD on nodes\n')
    #nfds = AppManager(ndn, ndn.net.hosts, Nfd)

    # MiniNDNCLI(ndn.net)

    ndn.stop()
