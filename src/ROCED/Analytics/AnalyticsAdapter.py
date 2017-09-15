from __future__ import unicode_literals, absolute_import

#from Util.ScaleTools import Ssh
import sys
import argparse
import configparser
import os
from xml.dom import minidom
import time

from Core import MachineRegistry, Config, Adapter
from Core.Core import ScaleCoreFactory
# in order to use the configKeys (and surely other things I might use later), it needs to inherit from Adapter
from Core.Adapter import AdapterBase, AdapterBoxBase
import getpass

from Util import ScaleTools

class AnalyticsAdapter(AdapterBase):
    #retrieve the configuration in order to know slurm_partition and e.g. keys
    
    configFreiburgUser = "freiburg_user"
    configFreiburgKey = "freiburg_key"
    configFreiburgServer = "freiburg_server"
    configSlurmUser = "slurm_user"
    configSlurmKey = "slurm_key"
    configSlurmServer = "slurm_server"
    configSlurmPartition = "slurm_partition"
    

    def __init__(self):
        AdapterBase.__init__(self)
        #super(AdapterBase, self).__init__()
        print("Running analytics tools for ROCED")
        self.addCompulsoryConfigKeys(self.configSlurmPartition, Config.ConfigTypeString, description="Slurm Partition name")

        self.addOptionalConfigKeys(self.configSlurmUser, datatype=Config.ConfigTypeString,
                                     description="Login name for slurm collector server.",
                                     default=getpass.getuser())
        self.addOptionalConfigKeys(key=self.configSlurmServer, datatype=Config.ConfigTypeString,
                                   description="Hostname of collector server. If machines are connected to connector "
                                   "and have commandline interface installed, localhost can easily be used "
                                   "because we query with \"global\".",
                                   default="localhost")
        self.addOptionalConfigKeys(key=self.configSlurmKey, datatype=Config.ConfigTypeString,
                                   description="Path to SSH key for remote login. Not necessary with server localhost.",
                                   default="~/")
    

        self.addOptionalConfigKeys(key=self.configSlurmServer, datatype=Config.ConfigTypeString,
                                   description="Hostname of collector server. If machines are connected to connector "
                                               "and have commandline interface installed, localhost can easily be used "
                                               "because we query with \"global\".",
                                   default="localhost")


    
        self.parser = argparse.ArgumentParser(description="ROCED analytics")
        self.parser.add_argument("--config", nargs=1,
                                 help="Run using a custom config file (default: %(default)s)",
                                 default="/etc/roced/roced.conf")
        self.parser.add_argument("--slurmfree",action="store_true",dest="slurmfree",help="slurmfree style output")
        self.parser.add_argument("--susers",action="store_true",help="susers style output")
        self.parser.add_argument("--verbose",'-v',dest="verbose", action="store_true")

        self.args = vars(self.parser.parse_args())
        print("ROCED analytics configured with config file: {}" .format( self.args["config"][0] ))
        
        self.config = configparser.RawConfigParser()
        self.config.readfp(open(self.args["config"][0]))

        if self.args["verbose"]:
            print("Writing current conf to myconf.txt")
            self.config.write(open('myconf.txt','wb')) 
        
        self.hostDict = {}
        self.listOfHosts = []

        self.userDict = {}
        self.listOfUsers = []

    def fillHostDict(self):
        """
        Fills a dictionary with the { hostname : { "owner": owner, "status" : status} }
        from the information gathered from slurm (hostnames, status) and from nemo/Moab (owner)
        """
        for nodename in self.listOfHosts:
            if nodename not in self.hostDict.keys():
                self.hostDict[nodename] = {}
        

        freiburg_users = ["fr_ms1414","fr_herten","fr_cw97"]
        freiburg_key = self.config.get("freiburg_cloud",self.configFreiburgKey)
        freiburg_server = self.config.get("freiburg_cloud",self.configFreiburgServer)

        print("Considering the following NEMO user accounts: {}".format( ', '.join(freiburg_users) ) )


        for user in freiburg_users:
            print(freiburg_server, user, freiburg_key)
            frSsh = ScaleTools.Ssh(freiburg_server, user, freiburg_key)
            cmd="checkjob ALL --xml"
            frResult = frSsh.handleSshCall(call=cmd, quiet=False)
            print ("trying to log into {}".format(freiburg_server))
            if frResult[0] != 0:
                print ("SSH connection to NEMO via {} could not be established, error {}.".format(freiburg_server, frResult[0]))
                for nodename in self.listOfHosts:
                    self.hostDict[ nodename]["owner"] = "unknown"
                
                
            elif frResult[0] == 0:
                itemlist = minidom.parseString(frResult[1]).getElementsByTagName('job')
                for li in itemlist:
                    if li.attributes['State'].value == "Running":
                        var = li.getElementsByTagName('Variable')
                        for v in var:
                            if v.getAttribute('name') == 'VM_IP':
                                vmIP=v.childNodes[0].nodeValue
                                hostname="host-"+vmIP.replace('.','-')
                                if hostname in self.hostDict.keys():
                                    self.hostDict[ hostname]["owner"] = user
                                
        return self.hostDict


    def moabOwnerForIP(self,vmIP):
        """
        deprecated: gets the owner for one specific job - takes too many ssh connections 
        (3 per host, instead of 3)
        """
        #ssh for all three accounts to NEMO to check which Host/IP belongs to which account
        freiburg_users = ["fr_ms1414","fr_herten","fr_cs97"]
        freiburg_key = self.config.get("freiburg_cloud",self.configFreiburgKey)
        freiburg_server = self.config.get("freiburg_cloud",self.configFreiburgServer)

        if self.args["verbose"]:
            print("Considering the following NEMO user accounts: {}".format( ', '.join(freiburg_users) ) )

        for user in freiburg_users:
            frSsh = ScaleTools.Ssh(freiburg_server, user, freiburg_key)
            cmd="checkjob ALL --xml"
            frResult = frSsh.handleSshCall(call=cmd, quiet=True)
            if frResult[0] == 0:
                itemlist = minidom.parseString(frResult[1]).getElementsByTagName('job')
                #print( "{} {}".format(user,frSsh.handleSshCall(call=cmd, quiet=True)[1]))
                #if the VM-IP
                for li in itemlist:
                    if li.attributes['State'].value == "Running":
                        var = li.getElementsByTagName('Variable')
                        for v in var:
                            if v.getAttribute('name') == 'VM_IP':
                                if v.childNodes[0].nodeValue == vmIP:
                                    return user

    def sinfoFromSlurm(self):

        slurm_server = self.config.get("slurm_req_freiburg",self.configSlurmServer)
        slurm_partition = self.config.get("slurm_req_freiburg",self.configSlurmPartition)
        slurm_user = self.config.get("slurm_req_freiburg",self.configSlurmUser)
        slurm_key = self.config.get("slurm_req_freiburg",self.configSlurmKey)
        slurm_ssh = ScaleTools.Ssh(slurm_server, slurm_user, slurm_key)
        
        
        cmd =  ("sinfo -h -l -N -p {} --format %n,%C,%T " ).format( slurm_partition )
        results_sinfo = slurm_ssh.handleSshCall(call=cmd, quiet=False) 
        #this contains all nodes, also those that are down
        results_sinfo = slurm_ssh.handleSshCall(call=cmd, quiet=True) 
        slurm_result_status = results_sinfo[0]
        slurm_result_sinfos = results_sinfo[1] + "\n"
        slurm_ssh_error = str(results_sinfo[2])

        #this gives the sinfo output for ALL machines, even those that are down
        #put slurm_result together in the way it is needed:
        slurm_result = (slurm_result_status,  slurm_result_sinfos , slurm_ssh_error)
        return slurm_result

    def parse_sinfo_output(self,output):
        nlist = []
        for line in output.splitlines():
            if line.split(',')[0] not in nlist:
                nlist.append(line.split(','))
        return nlist

    def getIPFromHostname(self,hostname):
        IP=hostname.replace('host-','').replace('-','.')
        return IP


    def fillNodeList (self):
        slurm_result= self.sinfoFromSlurm()
        if slurm_result[0] != 0:
            raise ValueError("SSH connection to Slurm collector could not be established.")
        for n in self.parse_sinfo_output(slurm_result[1]):
            hostname = n[0]
            slotsstring = n[1]
            self.listOfHosts.append(hostname)
            #add the slots already to the dictionary hostDict here
            if hostname not in self.hostDict.keys():
                self.hostDict[hostname] = {}
            self.hostDict[hostname]["slots"] = slotsstring
            self.hostDict[hostname]["status"] = n[2]

        return self.listOfHosts, self.hostDict

    def convertSlots(self,slotsstring):
        slots = slotsstring.split('/')
        nAllocated = int(slots[0])
        nIdle = int(slots[1])
        nOther = int (slots[2] )#e.g. drained
        
        nIdle += nOther
        text = nAllocated*"x" + nIdle*"-"
        
        return text

    def getSusers(self):
        slurm_server = self.config.get("slurm_req_freiburg",self.configSlurmServer)
        slurm_partition = self.config.get("slurm_req_freiburg",self.configSlurmPartition)
        slurm_user = self.config.get("slurm_req_freiburg",self.configSlurmUser)
        slurm_key = self.config.get("slurm_req_freiburg",self.configSlurmKey)
        slurm_ssh = ScaleTools.Ssh(slurm_server, slurm_user, slurm_key)
        
        
        cmd =  ("squeue -p {} -h --format %u,%T,%C" ).format( slurm_partition )
        results_squeue = slurm_ssh.handleSshCall(call=cmd, quiet=False) 
        if results_squeue[0] != 0:
            raise ValueError("SSH connection to Slurm collector could not be established.")
        
        userlist = self.parse_squeue(results_squeue[1])

        

        utext = []
        utext.append("\n")

        utext.append("User".ljust(10) + "RUNNING".ljust(10) + "PENDING".ljust(10))
        utext.append(30*"=")


        _statepr = {}

        for u in self.listOfUsers:
            _us=u.ljust(10)
            for _s in ["RUNNING","PENDING"]:
                _statepr[_s]=10*" "
                if _s in self.userDict[u].keys():
                    _statepr[_s]=str(self.userDict[u][_s]).ljust(10)
            utext.append(_us + _statepr["RUNNING"] + _statepr["PENDING"])
        for i in utext:
            print i



    def parse_squeue(self,results_squeue):
        for line in results_squeue.splitlines():
            _ulist = line.split(',')
            
            _user = _ulist[0]
            if _user not in self.listOfUsers:
                self.listOfUsers.append(_user)
            if _user not in self.userDict.keys():
                self.userDict[_user] = {}
            _state=_ulist[1]
            _ncores=_ulist[2]
            if _state in self.userDict[_user].keys():
                self.userDict[_user][_state] += int(_ncores)
            else:
                self.userDict[_user][_state] = int(_ncores)

        return 


    def getSlurmfree(self):
        self.fillNodeList()
        self.fillHostDict()

        if len(self.listOfHosts) == 0:
            print ("No virtual BFG hosts running at the moment")
            return
        stext = []
        stext.append("\n")
        stext.append("Hostname".ljust(18) + "Owner".ljust(14) +"Slots".ljust(14) +"status".ljust(12)) 
        stext.append("host-10-18-x-y".ljust(18) + "VMjob".ljust(12))
        stext.append(58*"=") 

        for n in self.listOfHosts:
            if n in self.hostDict.keys():
                if "down" in self.hostDict[n]["status"]:
                    continue
                owner = self.hostDict[n]["owner"].ljust(14)
                slots = self.convertSlots(self.hostDict[n]["slots"]).ljust(14)
                status = self.hostDict[n]["status"].ljust(14)
                
            else: 
                owner = "n/a".ljust(10)
                slots = "n/a".ljust(8)
                status = "n/a".ljust(14)

            
            stext.append(n.ljust(18) + owner  +slots + status)
        for s in stext:
            print s


        


if __name__ == "__main__":

    
    anatool = AnalyticsAdapter()



    if anatool.args["slurmfree"]:
        print( "Querying info on running machines for partition: %s" %(anatool.config.get("slurm_req_freiburg",anatool.configSlurmPartition)) )
        anatool.getSlurmfree()

    elif anatool.args["susers"]:
        print( "\nUser jobs in n(CPU) running or pending for virtual machines on NEMO" )
        anatool.getSusers()
