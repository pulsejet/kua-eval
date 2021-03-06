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

import random
from time import sleep, time_ns
from joblib import Parallel, delayed

from mininet.log import setLogLevel, info
from mininet.topo import Topo

from minindn.minindn import Minindn
from minindn.util import MiniNDNCLI
from minindn.apps.app_manager import AppManager
from minindn.apps.application import Application
from minindn.apps.nfd import Nfd
from minindn.apps.nlsr import Nlsr
from minindn.helpers.nfdc import Nfdc
from minindn.helpers.ndn_routing_helper import NdnRoutingHelper
from minindn.helpers.ip_routing_helper import IPRoutingHelper

# Configuration
USE_REDIS = False

# Auto filled
SERV_IP = ""

def collect_stats(node):
    rx_packets, tx_packets, rx_bytes, tx_bytes = 0, 0, 0, 0

    intflist = node.intfNames()
    intfliststr = ' '.join(intflist)
    output = node.cmd('/mini-ndn/kmn/stat.sh {}'.format(intfliststr)).splitlines()
    output = [line.strip() for line in output]

    for i, intf in enumerate(intflist):
        count = 4
        rx_packets += int(output[i*count+0])
        tx_packets += int(output[i*count+1])
        rx_bytes += int(output[i*count+2])
        tx_bytes += int(output[i*count+3])

    return (rx_packets, tx_packets, rx_bytes, tx_bytes)

def collect_all_stats(id, net):
    rx_packets, tx_packets, rx_bytes, tx_bytes = 0, 0, 0, 0

    # results = [collect_stats(node) for node in net.hosts]
    results = Parallel(n_jobs=-1, require='sharedmem',
                       prefer="threads")(delayed(collect_stats)(node) for node in net.hosts)

    # sum up all results
    for result in results:
        rx_packets += result[0]
        tx_packets += result[1]
        rx_bytes += result[2]
        tx_bytes += result[3]

    with open('/mini-ndn/kmn/results.csv', 'a') as file:
        file.write("{},{},{},{},{},{}\n".format(
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

class KuaNode(Application):
    def __init__(self, node):
        Application.__init__(self, node)
        self.name = '/knode-{}'.format(node.name)

    def start(self):
        Application.start(
            self, '/mini-ndn/kmn/kua/build/bin/kua /kua {}'.format(self.name), logfile='kua.log')

class KuaMaster(Application):
    def start(self):
        Application.start(
            self, '/mini-ndn/kmn/kua/build/bin/kua-master /kua /master', logfile='kua-master.log')

class Cli11(Application):
    def start(self):
        command = 'python3 /mini-ndn/kmn/cli11.py {}'.format(SERV_IP)
        if not USE_REDIS:
            command = '/mini-ndn/kmn/kua-cli11.sh'

        Application.start(self, command, logfile='cli11.log')

class Cli12(Application):
    def start(self):
        Application.start(
            self, 'python3 /mini-ndn/kmn/cli12.py {}'.format(SERV_IP), logfile='cli12.log')

if __name__ == '__main__':
    setLogLevel('info')

    Minindn.cleanUp()
    Minindn.verifyDependencies()

    ndn = Minindn()

    ndn.start()

    storageNodes = [h for h in ndn.net.hosts if h.name[0] == 'r']
    clusternode = storageNodes[0]

    if USE_REDIS:
        # Calculate all routes for IP routing
        IPRoutingHelper.calcAllRoutes(ndn.net)
        info("IP routes configured\n")

        info('Starting redis\n')
        redis = AppManager(ndn, storageNodes, Redis)

        sleep(1)

        info('Starting redis cluster\n')
        random.shuffle(storageNodes)
        hostlist = ""
        for h in storageNodes:
            hostlist += h.IP() + ':6379 '
        cmd = 'redis-cli --cluster create --cluster-yes --cluster-replicas 2 {}'.format(
            hostlist)
        info(clusternode.cmd(cmd))
        sleep(1)

        SERV_IP = clusternode.IP()

    else:
        info('Starting NFD on nodes\n')
        nfds = AppManager(ndn, ndn.net.hosts, Nfd)

        info('Starting NLSR on nodes\n')
        nlsrs = AppManager(ndn, ndn.net.hosts, Nlsr)

        sleep(2)

        info('Adding static routes to NFD\n')
        grh = NdnRoutingHelper(ndn.net, 'udp', 'link-state')
        grh.addOrigin(storageNodes, ['/kua/sync'])
        grh.calculateNPossibleRoutes()

        info('Setting NFD strategy to multicast on all nodes with prefix\n')
        for node in ndn.net.hosts:
            Nfdc.setStrategy(node, "/kua/sync", Nfdc.STRATEGY_MULTICAST)

        info('Starting Kua nodes\n')
        kuas = AppManager(ndn, storageNodes, KuaNode)
        sleep(5)

        info('Starting Kua master\n')
        kuamaster = AppManager(ndn, [clusternode], KuaMaster)
        sleep(30)

    # Get client nodes
    cli1 = ndn.net.get('cli1')
    cli2 = ndn.net.get('cli2')
    cli3 = ndn.net.get('cli3')

    # Collect stats
    collect_all_stats(0, ndn.net)

    # Collect stats till process exits
    curr_time = 1
    def collect_for(app_managers):
        global curr_time
        period = 0.1
        while True:
            running = False
            for am in app_managers:
                if am.apps[0].process.poll() is None:
                    running = True
                    break
            if not running:
                break

            collect_all_stats(round(curr_time*period, 1), ndn.net)
            curr_time += 1
            sleep(period)

    # Start insertion
    cli11 = AppManager(ndn, [cli1], Cli11)
    collect_for([cli11])

    # cli12 = AppManager(ndn, [cli1], Cli12)
    # collect_for([cli12])

    # cli12 = AppManager(ndn, [cli1], Cli12)
    # cli22 = AppManager(ndn, [cli2], Cli12)
    # collect_for([cli12, cli22])

    # cli12 = AppManager(ndn, [cli1], Cli12)
    # cli22 = AppManager(ndn, [cli2], Cli12)
    # cli23 = AppManager(ndn, [cli3], Cli12)
    # collect_for([cli12, cli22, cli23])

    # MiniNDNCLI(ndn.net)

    ndn.stop()
