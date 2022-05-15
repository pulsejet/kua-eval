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

from mininet.log import setLogLevel, info
from mininet.topo import Topo

from minindn.minindn import Minindn
from minindn.util import MiniNDNCLI
from minindn.apps.app_manager import AppManager
from minindn.apps.application import Application
from minindn.apps.nfd import Nfd
from minindn.helpers.ndn_routing_helper import NdnRoutingHelper
from minindn.helpers.ip_routing_helper import IPRoutingHelper


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

    info('Starting redis cluster\n')
    clnode = storageNodes[0]
    hostlist = ""
    for h in storageNodes:
        hostlist += h.IP() + ':6379 '
    cmd = 'redis-cli --cluster create --cluster-yes --cluster-replicas 1 {}'.format(
        hostlist)
    print(clnode.cmd(cmd))

    #info('Starting NFD on nodes\n')
    #nfds = AppManager(ndn, ndn.net.hosts, Nfd)

    MiniNDNCLI(ndn.net)

    ndn.stop()
