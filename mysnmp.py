#!/usr/bin/env python3
from pysnmp.hlapi import *

class mqttSNMP():
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.errorIndic = None
        self.status = None
        self.name = ""
        self.value = ""

    def get(self, oid, community):
        iterator = getCmd(SnmpEngine(), CommunityData(community), UdpTransportTarget((self.host, self.port), timeout = 1, retries=0), ContextData(), ObjectType(ObjectIdentity(oid)))
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
        if errorIndication:
            self.errorIndic = errorIndication
            return ("Error in Polling : %s" % self.errorIndic)
        else:
            if errorStatus:
                self.status = errorStatus.prettyPrint()
                return ("Error in Polling : %s" % self.status)
            else:
                self.name, self.value = varBinds[0]
                return('%s : %s' % (self.name, self.value))


    def getNext(self, oid, community):
        iterator = nextCmd(SnmpEngine(), CommunityData(community),  UdpTransportTarget((self.host, self.port), timeout = 1, retries=0), ContextData(), ObjectType(ObjectIdentity(oid)))
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
        if errorIndication:
            self.errorIndic = errorIndication
            return ("Error in Polling : %s" % self.errorIndic)
        else:
            if errorStatus:
                self.status = errorStatus.prettyPrint()
                return ("Error in Polling : %s" % self.status)
            else:
                self.name, self.value = varBinds[0]
                return('%s : %s' % (self.name, self.value))


##        def getBulk(self, oid):
##                iterator = bulkCmd(SnmpEngine(), CommunityData('public'),  UdpTransportTarget((host, 161)), ContextData(), 0, 25, ObjectType(ObjectIdentity(oid)))
##                errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
##                if errorIndication:
##                        print(errorIndication)
##                else:
##                        if errorStatus:  # SNMP agent errors
##                                print('%s at %s' % (errorStatus.prettyPrint(), varBinds[int(errorIndex)-1] if errorIndex else '?'))
##                        else:
##                                for varBind in varBinds:  # SNMP response contents
##                                        print(varBind )
##                                        #print(' = '.join([x.prettyPrint() for x in varBind]))
##
##        def walk(self, oid):
##            for (errorIndication,errorStatus,errorIndex,varBinds) in nextCmd(SnmpEngine(), 
##                CommunityData('public'), UdpTransportTarget((host, 161)), ContextData(), 
##                ObjectType(ObjectIdentity(oid)), lexicographicMode=False):
##                if errorIndication:
##                    print(errorIndication, file=sys.stderr)
##                    break
##                elif errorStatus:
##                    print('%s at %s' % (errorStatus.prettyPrint(),
##                                        errorIndex and varBinds[int(errorIndex) - 1][0] or '?'), 
##                                        file=sys.stderr)             
##                    break
##                else:
##                    for varBind in varBinds:
##                        print(varBind)
