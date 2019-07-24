#!/usr/bin/env python3
from pysnmp.hlapi import *
import datetime

class mqttSNMP():
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.errorIndic = None
        self.status = None
        self.name = ""
        self.value = ""
        self.pollError = False
        self.data = {}

    def get(self, oid, community):
        self._clearFields()
        self.name = oid
        try:
            iterator = getCmd(SnmpEngine(),
            CommunityData(community),
            UdpTransportTarget((self.host, self.port),
            timeout = 1, retries=0),
            ContextData(), ObjectType(ObjectIdentity(oid)))

            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            if errorIndication:
                self.errorIndic = self.value = errorIndication
            else:
                if errorStatus:
                    self.status = self.value = "Could Not Issue Get-Next Request"
                else:
                    self.name, self.value = varBinds[0]

        except:
            self.pollError = True
            self.errorIndic =  "Error"
            self.status = self.value ="Could Not Issue Get-Next Request"


        return self._constructResp()



    def getNext(self, oid, community):
        self._clearFields()
        self.name =  oid
        try:
            iterator = nextCmd(SnmpEngine(),
            CommunityData(community),
            UdpTransportTarget((self.host, self.port),
            timeout = 1, retries=0),
            ContextData(),
            ObjectType(ObjectIdentity(oid)))

            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

            if errorIndication:
                self.errorIndic = self.value = errorIndication
            else:
                if errorStatus:
                    self.status = self.value ="Could Not Issue Get-Next Request"
                else:
                    self.name, self.value = varBinds[0]
        except:
            self.pollError = True
            self.errorIndic = "Error"
            self.status = self.value ="Could Not Issue Get-Next Request"

        return self._constructResp()



    def _constructResp(self):
        self.data['Error Indication'] = ("%s" % self.errorIndic)
        self.data['Error Status'] = ("%s" % self.status)
        self.data['OID'] = ("%s" % self.name)
        self.data['Value'] = ("%s" % self.value)
        self.data['Time'] = ("%s" % datetime.datetime.now())
        self.data['Poll Error'] = self.pollError
        self.data['Host'] = self.host
        self.data['Port'] = self.port

        return self.data

    def _clearFields(self):
        self.errorIndic = None
        self.status = None
        self.value = ""
        self.data = {}

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
