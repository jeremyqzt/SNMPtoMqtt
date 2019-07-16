#!/usr/bin/python3

import threading
import time
import os
import sys
import json
import paho.mqtt.client as paho
import json

import mysnmp

class pollThread (threading.Thread):
    def __init__(self, name, southConfig, northConfig, mqtt):
        threading.Thread.__init__(self)
        self.name = name

        southCfg = json.loads(southConfig) #Attached devices = southbound
        northCfg = json.loads(northConfig) #The Cloud = northbound

        self.delay = int(southCfg['interval'])

        self.SnmpIp = southCfg['addr']
        self.SnmpPort = int(southCfg['port'])
        self.SnmpOper = southCfg['snmpOper']
        self.community = "public"
        self.OID = southCfg['oid']

        self.lastWillTopic = northCfg['lastWillTopic']
        self.lastWill = northCfg['lastWill']

        self.MqttIp = northCfg['addr']
        self.MqttPort = int(northCfg['port'])
        self.clientId = northCfg['clientId']
        self.user = northCfg['username']
        self.password = northCfg['password']
        self.topic = southCfg['topic']
        self.keepAlive = int(northCfg['keepAlive'])

        self.SnmpResp = ""
        self.MqttSuccess = False

        self.SnmpAgent = mysnmp.mqttSNMP(self.SnmpIp, self.SnmpPort)

        self.mqttClient = mqtt

        self.running = True
        self.data = {}
        self.JSONdata = None
    def run(self):

        while (self.running):

            self._poll()
            self._send()

            for i in range(self.delay):
                time.sleep(1)

                if not self.running:
                    return


    def setRunning(self, newVal):
        self.running = newVal

    def getRunning(self):
        return self.running

    def getHost(self):
        return self.SnmpIp

    def getPort(self):
        return str(self.SnmpPort)

    def getLastResp(self):
        return self.SnmpResp

    def _poll(self):
        if (self.SnmpOper == "Get"):
            self.SnmpResp = self.SnmpAgent.get(self.OID, self.community)
        else:
            self.SnmpResp = self.SnmpAgent.getNext(self.OID, self.community)


        print(self.snmpResp)
        self.data['Error Indication'] = ("%s" % self.SnmpAgent.errorIndic)
        self.data['Error Status'] = ("%s" % self.SnmpAgent.status)
        self.data['OID'] = ("%s" % self.SnmpAgent.name)
        self.data['Value'] = ("%s" % self.SnmpAgent.value)
        self.data['Topic'] = self.topic
        self.JSONdata = json.dumps(self.data)


    def _send(self):
        self.mqttClient.publish(self.topic, self.JSONdata)


