#!/usr/bin/python3

import threading
import time
import os
import sys
import json
import paho.mqtt.client as paho
import json
import datetime

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
        self.SnmpOper = int(southCfg['snmpOper'])
        self.compareOper = int(southCfg['operEnum'])
        self.compareTo = southCfg['compare']

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

        self.SnmpResp = {}
        self.MqttSuccess = False

        self.SnmpAgent = mysnmp.mqttSNMP(self.SnmpIp, self.SnmpPort)

        self.mqttClient = mqtt
        self.oldSnmpResp = None

        self.running = True
        self.data = {}
        self.JSONdata = None
        self.lastPublish = ""

    def run(self):

        while (self.running):
            self._poll()
            if (self._compare()):
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
        if (self.SnmpOper == 0):
            self.SnmpResp = self.SnmpAgent.get(self.OID, self.community)
        elif (self.SnmpOper == 1):
            self.SnmpResp = self.SnmpAgent.getNext(self.OID, self.community)

        self.SnmpResp['Topic'] = self.topic #add topic back
        self.SnmpResp['Publish'] = self.lastPublish
        self.JSONdata = json.dumps(self.SnmpResp)

    def _send(self):
        self.lastPublish = ("%s" % datetime.datetime.now())
        self.SnmpResp['Publish'] = self.lastPublish
        self.JSONdata = json.dumps(self.SnmpResp)

        self.oldSnmpResp = self.SnmpResp
        self.mqttClient.publish(self.topic, self.JSONdata)

    def _compare(self):
        compareOper = self.compareOper
        if self.oldSnmpResp is None: #First Publish
            return True

        if (compareOper == 0):
            return true if self.SnmpResp['Value'] != self.oldSnmpResp['Value'] else False
        if (compareOper == 1):
            return True if self.SnmpResp['Value'] == self.oldSnmpResp['Value'] else False
        if (compareOper == 2):
            return True
        if (compareOper == 3):
            return True if self.SnmpResp['Value'] >= self.oldSnmpResp['Value']  else False
        if (compareOper == 4):
            return True if self.SnmpResp['Value'] > self.oldSnmpResp['Value']  else False
        if (compareOper == 5):
            return True if self.SnmpResp['Value'] <= self.oldSnmpResp['Value']  else False
        if (compareOper == 6):
            return True if self.SnmpResp['Value'] < self.oldSnmpResp['Value']  else False
        if (compareOper == 7):
            return True if self.SnmpResp['Value'].contains(self.compareTo)  else False
        if (compareOper == 8):
            return True if self.SnmpResp['Value'] == self.compareTo  else False


