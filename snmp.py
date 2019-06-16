#!/usr/bin/env python3
from pysnmp.hlapi import *


def getBulk(host, oid):
	iterator = bulkCmd(SnmpEngine(), CommunityData('public'),  UdpTransportTarget((host, 161)), ContextData(), 0, 25, ObjectType(ObjectIdentity(oid)))
	errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
	if errorIndication:
		print(errorIndication)
	else:
		if errorStatus:  # SNMP agent errors
			print('%s at %s' % (errorStatus.prettyPrint(), varBinds[int(errorIndex)-1] if errorIndex else '?'))
		else:
			for varBind in varBinds:  # SNMP response contents
				print(varBind )
				#print(' = '.join([x.prettyPrint() for x in varBind]))

def walk(host, oid):
    for (errorIndication,errorStatus,errorIndex,varBinds) in nextCmd(SnmpEngine(), 
        CommunityData('public'), UdpTransportTarget((host, 161)), ContextData(), 
        ObjectType(ObjectIdentity(oid)), lexicographicMode=False):
        if errorIndication:
            print(errorIndication, file=sys.stderr)
            break
        elif errorStatus:
            print('%s at %s' % (errorStatus.prettyPrint(),
                                errorIndex and varBinds[int(errorIndex) - 1][0] or '?'), 
                                file=sys.stderr)             
            break
        else:
            for varBind in varBinds:
                print(varBind)

def get(host, oid):
	iterator = getCmd(SnmpEngine(), CommunityData('public'),  UdpTransportTarget((host, 161)), ContextData(), ObjectType(ObjectIdentity(oid)))
	errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
	if errorIndication:
		print(errorIndication)
	else:
		if errorStatus:  # SNMP agent errors
			print('%s at %s' % (errorStatus.prettyPrint(), varBinds[int(errorIndex)-1] if errorIndex else '?'))
		else:
			for varBind in varBinds:  # SNMP response contents
				print(' = '.join([x.prettyPrint() for x in varBind]))

def getNext(host, oid):
	iterator = nextCmd(SnmpEngine(), CommunityData('public'),  UdpTransportTarget((host, 161)), ContextData(), ObjectType(ObjectIdentity(oid)))
	errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
	if errorIndication:
		print(errorIndication)
	else:
		if errorStatus:  # SNMP agent errors
			print('%s at %s' % (errorStatus.prettyPrint(), varBinds[int(errorIndex)-1] if errorIndex else '?'))
		else:
			for varBind in varBinds:  # SNMP response contents
				print(' = '.join([x.prettyPrint() for x in varBind]))

getBulk('192.168.0.50','1.3.6.1.2.1.47.1.1.1.1.2')
#get('192.168.0.50','1.3.6.1.2.1.47.1.1.1.1.2')