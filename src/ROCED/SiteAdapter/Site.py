# ===============================================================================
#
# Copyright (c) 2010, 2011, 2015, 2016 by Georg Fleig, Frank Fischer,
# Thomas Hauth and Stephan Riedel
#
# This file is part of ROCED.
#
# ROCED is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ROCED is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ROCED.  If not, see <http://www.gnu.org/licenses/>.
#
# ===============================================================================


import abc
import copy
import logging

from Core import Config
from Core import MachineRegistry
from Core.Adapter import AdapterBase, AdapterBoxBase


class SiteInformation(object):
    def __init__(self):
        self.siteName = None
        self.baselineMachines = 0
        self.maxMachines = 0
        self.supportedMachineTypes = []
        self.cost = 0
        self.isAvailable = True

    def siteName():  # @NoSelf
        doc = """Docstring"""  # @UnusedVariable

        def fget(self):
            return self._siteName

        def fset(self, value):
            self._siteName = value

        def fdel(self):
            del self._siteName

        return locals()

    siteName = property(**siteName())

    def baselineMachines():  # @NoSelf
        doc = """Docstring"""  # @UnusedVariable

        def fget(self):
            return self._baselineMachines

        def fset(self, value):
            self._baselineMachines = value

        def fdel(self):
            del self._baselineMachines

        return locals()

    baselineMachines = property(**baselineMachines())

    def maxMachines():  # @NoSelf
        doc = """Docstring"""  # @UnusedVariable

        def fget(self):
            return self._maxMachines

        def fset(self, value):
            self._maxMachines = value

        def fdel(self):
            del self._maxMachines

        return locals()

    maxMachines = property(**maxMachines())

    def supportedMachineTypes():  # @NoSelf
        doc = """Docstring"""  # @UnusedVariable

        def fget(self):
            return self._supportedMachineTypes

        def fset(self, value):
            self._supportedMachineTypes = value

        def fdel(self):
            del self._supportedMachineTypes

        return locals()

    supportedMachineTypes = property(**supportedMachineTypes())

    def cost():  # @NoSelf
        doc = """Docstring"""  # @UnusedVariable

        def fget(self):
            return self._cost

        def fset(self, value):
            self._cost = value

        def fdel(self):
            del self._cost

        return locals()

    cost = property(**cost())

    # if true, this site is available to run new nodes.
    # If a site is not available, already running nodes keep running
    def isAvailable():  # @NoSelf
        doc = """Docstring"""  # @UnusedVariable

        def fget(self):
            return self._isAvailable

        def fset(self, value):
            self._isAvailable = value

        def fdel(self):
            del self._isAvailable

        return locals()

    isAvailable = property(**isAvailable())


class SiteAdapterBase(AdapterBase):
    """
    Abstract base class for specific cloud site information.
    """
    __metaclass__ = abc.ABCMeta

    ConfigSiteName = "site_name"
    ConfigSiteType = "site_type"
    ConfigSiteDescription = "site_description"
    ConfigMachines = "machines"
    ConfigIsAvailable = "is_available"
    ConfigCost = "cost"
    ConfigMaxMachines = "max_machines"
    ConfigMachineBootTimeout = "machine_boot_timeout"
    ConfigBaselineMachines = "baseline_machines"

    # Override the following for your custom cloud implementation
    @abc.abstractmethod
    def __init__(self):
        super(SiteAdapterBase, self).__init__()

        self.setConfig(self.ConfigSiteName, "default-site")
        self.setConfig(self.ConfigSiteDescription, "DefaultDescription")
        self.setConfig(self.ConfigIsAvailable, True)
        self.setConfig(self.ConfigCost, 0)
        self.setConfig(self.ConfigMaxMachines, None)  # None means: no limit

        self.setConfig(self.ConfigBaselineMachines, 0)
        self.setConfig(self.ConfigMachineBootTimeout, 300)

        self.addCompulsoryConfigKeys(self.ConfigSiteName, Config.ConfigTypeString)

        self.addOptionalConfigKeys(self.ConfigMachines, Config.ConfigTypeDictionary, default={})
        self.addOptionalConfigKeys(self.ConfigIsAvailable, Config.ConfigTypeBoolean, default=True)
        self.addOptionalConfigKeys(self.ConfigMachineBootTimeout, Config.ConfigTypeInt, default=30)
        self.addOptionalConfigKeys(self.ConfigMaxMachines, Config.ConfigTypeInt, default=10)

        self.logger = logging.getLogger('Site')

    @abc.abstractmethod
    def spawnMachines(self, machineType, count):
        """
        Spawn machines on the corresponding cloud site.

        :param machineType:
        :param count:
        :return:
        """
        pass

    def terminateMachines(self, machineType, count):
        """
        Terminate machine(s) on the corresponding site.

        This *should* be redefined but doesn't /have to/. There are other ways to handle
        termination (e.g.: automatic timeout/shutdown).

        :param machineType:
        :param count:
        """
        pass

    ###
    # The following functions shouldn't be required to be overwritten
    ###
    def getSiteMachines(self, status=None, machineType=None):
        # type: (str, str) -> Dict
        """
        Return dictionary with machines running on this site (Machine registry).

        :param status: (optional) filter on machine status
        :param machineType: (optional) filter on machine type
        :return {machine_id: {a:b,c:d,e:f}, machine_id: {a:b,c:d,e:f}, ...}:
        """
        mr = MachineRegistry.MachineRegistry()
        return mr.getMachines(self.getSiteName(), status, machineType)

    def applyMachineDecision(self, decision):

        decision = copy.deepcopy(decision)
        running_machines_count = self.getRunningMachinesCount()
        max_machines = self.getConfig(self.ConfigMaxMachines)

        for (machine_type, n_machines) in decision.items():
            # calc relative value when there are already machines running
            n_running_machines = 0
            if machine_type in running_machines_count:
                n_running_machines = running_machines_count[machine_type]
                decision[machine_type] -= n_running_machines

            # spawn
            if decision[machine_type] > 0:
                # TODO: Implement max_machines per site, not per machine type!!!
                # respect site limit for max machines for spawning but don't remove machines when
                # above limit this limit is currently implemented per machine type, not per site!
                if max_machines and (decision[machine_type] + n_running_machines) > max_machines:
                    self.logger.info(
                        "Request exceeds maximum number of allowed machines on this site (" +
                        str(decision[machine_type] + n_running_machines) + ">" + str(max_machines) +
                        ")! ")
                    self.logger.info("Will spawn " + str(
                            max(0, max_machines - n_running_machines)) + " machines.")
                    decision[machine_type] = max_machines - n_running_machines
                    # is the new decision valid?
                    if decision[machine_type] > 0:
                        self.spawnMachines(machine_type, decision[machine_type])
                else:
                    self.spawnMachines(machine_type, decision[machine_type])

            # terminate
            elif decision[machine_type] < 0:
                self.terminateMachines(machine_type, abs(decision[machine_type]))

    def getSiteMachinesAsDict(self, statusFilter=None):
        # type: (List) -> Dict
        """Retrieve machines running at a site. Optionally can filter on a status list.

        :return dictionary {machine_type: [machine ID, machine ID, ...], ...} :
        """
        if statusFilter is None:
            statusFilter = []

        myMachines = self.getSiteMachines()
        machineList = dict()

        for i in self.getConfig(self.ConfigMachines):
            machineList[i] = []

        for mid, machine in myMachines.items():
            if statusFilter:  # empty list returns false in this statement
                if machine.get(MachineRegistry.MachineRegistry.regStatus) in statusFilter:
                    machineList[machine[MachineRegistry.MachineRegistry.regMachineType]].append(mid)
            else:
                machineList[machine[MachineRegistry.MachineRegistry.regMachineType]].append(mid)

        return machineList

    def getRunningMachines(self):
        """Returns a dictionary of machines running at a specific site.

        :return dictionary {machine_type: [machine ID, machine ID, ...], ...} :
        """
        statusFilter = [MachineRegistry.MachineRegistry.statusBooting,
                        MachineRegistry.MachineRegistry.statusUp,
                        MachineRegistry.MachineRegistry.statusIntegrating,
                        MachineRegistry.MachineRegistry.statusWorking,
                        MachineRegistry.MachineRegistry.statusPendingDisintegration]
        return self.getSiteMachinesAsDict(statusFilter)

    def getRunningMachinesCount(self):
        """Return dictionary with number of machines running at a site.

        :return {machine_type: integer, ...}:
        """
        running_machines = self.getRunningMachines()
        running_machines_count = dict()
        for machine_type, midList in running_machines.items():
            running_machines_count[machine_type] = len(midList)
        return running_machines_count

    def getCloudOccupyingMachines(self):
        """Return all machines which occupy computing resources on the cloud.

        Same behaviour as getRunningMachines, just with other status filtering.

        :return dictionary {machine_type: [machine ID, machine ID, ...], ...} :
        """
        statusFilter = [MachineRegistry.MachineRegistry.statusBooting,
                        MachineRegistry.MachineRegistry.statusUp,
                        MachineRegistry.MachineRegistry.statusIntegrating,
                        MachineRegistry.MachineRegistry.statusWorking,
                        MachineRegistry.MachineRegistry.statusPendingDisintegration,
                        MachineRegistry.MachineRegistry.statusDisintegrating,
                        MachineRegistry.MachineRegistry.statusDisintegrated]
        return self.getSiteMachinesAsDict(statusFilter)

    def getCloudOccupyingMachinesCount(self):
        """Return total number of machines occupying computing resources on a site."""
        sum_ = 0
        for machineType, midList in self.getCloudOccupyingMachines().items():
            sum_ += len(midList)
        return sum_

    def isMachineTypeSupported(self, machineType):
        return machineType in self.getConfig(self.ConfigMachines)

    '''
    static information about the site
    '''

    def getSiteInformation(self):

        sinfo = SiteInformation()
        sinfo.siteName = self.getSiteName()
        sinfo.maxMachines = self.getConfig(self.ConfigMaxMachines)
        sinfo.baselineMachines = self.getConfig(self.ConfigBaselineMachines)
        sinfo.supportedMachineTypes = self.getConfig(self.ConfigMachines).keys()
        sinfo.cost = self.getConfig(self.ConfigCost)
        sinfo.isAvailable = self.getConfig(self.ConfigIsAvailable)

        return sinfo

    def getSiteName(self):
        return self.getConfig(self.ConfigSiteName)

    def getSiteType(self):
        return self.getConfig(self.ConfigSiteType)

    def getDescription(self):
        return self.getConfig(self.ConfigSiteDescription)


class SiteBox(AdapterBoxBase):
    def getRunningMachines(self):
        all_ = dict()

        for s in self.adapterList:
            all_[s.getSiteName()] = s.getRunningMachines()

        return all_

    def getRunningMachinesCount(self):
        all_ = dict()

        for s in self.adapterList:
            all_[s.getSiteName()] = s.getRunningMachinesCount()

        return all_

    def applyMachineDecision(self, decision):
        map(lambda x: x.applyMachineDecision(decision.get(x.getSiteName(), dict())),
            self.adapterList)

    def getSiteConfigAsDict(self):
        all_ = dict()

        for s in self.adapterList:
            all_[s.getSiteName()] = s.getConfigAsDict()

        return all_

    def getSite(self, siteName):
        res = filter(lambda x: x.getSiteName() == siteName, self.adapterList)
        if len(res) == 1:
            return res[0]
        else:
            return None

    def getSiteInformation(self):
        all_ = dict()

        for s in self.adapterList:
            all_[s.getSiteName()] = s.getSiteInformation()

        return all_
