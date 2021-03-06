from flask import Flask, flash, redirect, render_template, request, session, abort, url_for
import os
from os.path import isfile, join
import json
import sqlite3
import socket
import threading
import threadLoop
import paho.mqtt.client as paho
import ssl
import platform
import subprocess
from werkzeug import secure_filename
import logging

certPath = "certs"
app = Flask(__name__)

runningListCoor = []
lock = threading.Lock()
userSession = ""
mqttClient = None
cloudAddressStr = "Unattempted"
flag_connected = "Unattempted"
snmpTextEnum = ["Get", "Get-Next"]
compareTextEnum = ["Publish Different", "Publish Same", "Always Publish"
               , ">= (Greater Equal)", "> (Strictly Greater)", "<= (Lesser Equal)"
               , "< (Strictly Lesser)", "== (Contains)", "=== (Equals)"]
log = logging.getLogger(__name__)

def on_connect(client, userdata, flags, rc):
    pahoStatus = ["Successful", "Incorrect Protocol Version", "Invalid Client ID", "Server Unavailable", "Bad Credentials", "Not Authorized"]

    global flag_connected
    if (rc == 0):
      flag_connected = "Connected"
    else:
      flag_connected = "Disconencted - " + pahoStatus[rc]


def on_disconnect(client, userdata, rc):
    global flag_connected
    flag_connected = "Disconnected"


def stopAll():
    global mqttClient
    log.info(("Stopping polling"))
    for pollThread in runningListCoor:
        pollThread.setRunning(False)

    for pollThread in runningListCoor:
        pollThread.join()

    runningListCoor.clear()
    if mqttClient is not None:
      mqttClient.disconnect()

    mqttClient = None

def ping(ip, port):
    param = '-n' if platform.system().lower()=='windows' else '-c'
    command = ['ping', param, '1', ip]
    return subprocess.call(command) == 0

@app.route('/')
def home():
   if not session.get('logged_in'):
      return render_template('login.html')
   else:
      return redirect(url_for('saveDev'))


@app.route('/deleteFile', methods=['POST'])
def delete():
   if not session.get('logged_in'):
      return render_template('login.html')

   if request.method == 'POST':
      data = request.get_json()
      if not '/' in data:
         os.remove(certPath + "/" + data.strip('"'))
         onlyfiles = [f for f in os.listdir(certPath) if isfile(join(certPath, f))]

   return json.dumps({'success':True}), 200, {'ContentType':'application/json'}


@app.route('/saveCloud', methods=['POST', 'GET'])
def saveCloud():
   if not session.get('logged_in'):
      return render_template('login.html')

   if request.method == 'POST':
      data = request.get_json()
      sql = ' INSERT INTO cloudProfile(addr,port,lastWill,lastWillTopic,username,password,clientId,keepAlive, clientCert, caFile, clientKey) VALUES(?,?,?,?,?,?,?,?,?,?,?) '
      conn = sqlite3.connect('database.db')
      conn.execute('DELETE FROM cloudProfile;')
      conn.commit()
      log.info(("Cloud to Save: %s" % data))
      conn.execute(sql, (data['cloudAddr'], data['cloudPort'], data['lastWillMessage'], data['lastWillTopic'],
                         data['username'],data['password'], data['clientId'],data['keepAlive'], data['clientCert'],
                         data['caCert'],data['clientKey']))

      conn.commit()
      return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

   if request.method == 'GET':
      conn = sqlite3.connect('database.db')
      conn.row_factory = sqlite3.Row
      cursor = conn.execute("SELECT * FROM cloudProfile;")
      rows = cursor.fetchall()
      cloudData = [dict(ix) for ix in rows]
      onlyfiles = [f for f in os.listdir(certPath) if isfile(join(certPath, f))]

      conn.close()
      log.info(("cloud data being read: %s" % cloudData))
      if (cloudData):
         return render_template('clouds.html', cloud=cloudData, files=map(json.dumps, onlyfiles), filesCa=map(json.dumps, onlyfiles))
      else:
         return render_template('clouds.html', cloud=[], files=map(json.dumps, onlyfiles))


@app.route('/upload', methods=['POST', 'GET'])
def upload():
   if not session.get('logged_in'):
      return render_template('login.html')

   if request.method == 'POST':
      f = request.files['file']
      f.save(certPath + "/" + secure_filename(f.filename))
      onlyfiles = [f for f in os.listdir(certPath) if isfile(join(certPath, f))]
      return redirect(url_for('upload'))

   if request.method == 'GET':
      onlyfiles = [f for f in os.listdir(certPath) if isfile(join(certPath, f))]
      return render_template('upload.html', files=map(json.dumps, onlyfiles))



@app.route('/saveDev', methods=['POST', 'GET'])
def saveDev():
   if not session.get('logged_in'):
      return render_template('login.html')

   if request.method == 'POST':
      data = request.get_json()
      conn = sqlite3.connect('database.db')
      conn.execute('DELETE FROM devices;')
      sql = ' INSERT INTO devices(name,addr,port) VALUES(?,?,?) '
      log.info(("Devices to Save: %s" % data))
      for i in data:
            name = i['name'].strip()
            ip = i['ip'].strip()
            port = i['port'].strip()
            conn.execute(sql, (name, ip, port))

      conn.commit()
      conn.close()
      return json.dumps({'success':True}), 200, {'ContentType':'application/json'}
   if request.method == 'GET':
      conn = sqlite3.connect('database.db')
      conn.row_factory = sqlite3.Row
      cursor = conn.execute("SELECT * FROM devices;")
      rows = cursor.fetchall()
      dev = [dict(ix) for ix in rows]
      log.info(("getting devices %s" % dev))
      conn.close()

      return render_template('devices.html', devices=dev)

@app.route('/saveCoordinates', methods=['POST', 'GET'])
def saveCoordinates():
   if not session.get('logged_in'):
      return render_template('login.html')


   if request.method == 'POST':
      stopAll()
      data = request.get_json()
      conn = sqlite3.connect('database.db')
      conn.execute('DELETE FROM coordinates;')
      sql = ' INSERT INTO coordinates(oid, devName ,snmpOper, topic, interval, operEnum, compare) VALUES(?,?,?,?,?,?,?)'


      log.info(("Coordinates to Save: %s" % data))

      for i in data:
            oid = i['oid'].strip()
            snmpEnum = int(i['oper'].strip())
            interval = i['interval'].strip()
            topic = i['topic'].strip()
            name = i['name'].strip()
            operationEnum = int(i['operatorEnum'].strip())
            operText = i['operatorCompare'].strip()
            
            conn.execute(sql, (oid, name, snmpEnum, topic, interval, operationEnum, operText))

      conn.commit()
      conn.close()

      return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

   if request.method == 'GET':
      global snmpTextEnum, compareTextEnum
      conn = sqlite3.connect('database.db')
      conn.row_factory = sqlite3.Row
      cursor = conn.execute("SELECT * FROM devices;")
      rows = cursor.fetchall()
      dev = [dict(ix) for ix in rows]

      cursor = conn.execute("SELECT * FROM coordinates;")
      rows = cursor.fetchall()
      coordinates = [dict(ix) for ix in rows]
      for i in coordinates:
          i["snmpOperText"] = snmpTextEnum[int(i["snmpOper"])]
          i["operEnumText"] = compareTextEnum[int(i["operEnum"])]
      log.info(("Coordinates: %s" % coordinates))
      conn.close()

      return render_template('coordinate.html', devices=dev, coordinates=coordinates)


@app.route('/start', methods=['POST', 'GET'])
def engage():
    global cloudAddressStr
    global mqttClient
    if request.method == 'POST':
        data = request.get_json()
        if (data[0]['action'].strip() == "start"):
            conn = sqlite3.connect('database.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM coordinates LEFT JOIN devices WHERE coordinates.devName = devices.name;")
            rows = cursor.fetchall()
            coordinates = [dict(ix) for ix in rows]
            cursor = conn.execute("SELECT * FROM cloudProfile;")
            rows = cursor.fetchall()
            cloudResult = [dict(ix) for ix in rows]
            theCloud = cloudResult[0] #only supporting 1 cloud
            conn.close()


            #Kill Old Threads
            stopAll()

            #TODO: Abstract this 1 level higher
            mqttClient= paho.Client(theCloud['clientId'])
            mqttClient.on_connect = on_connect
            mqttClient.on_disconnect = on_disconnect

            caFileFP = certPath + "/" + theCloud['caFile'].strip()
            clientKeyFP = certPath + "/" + theCloud['clientKey'].strip()
            clientCertFP = certPath + "/" + theCloud['clientCert'].strip()
            cafile = caFileFP if os.path.exists(caFileFP) else None
            clientKey = clientKeyFP if os.path.exists(clientKeyFP) else None
            clientCert = clientCertFP if os.path.exists(clientCertFP) else None

            if ((theCloud['username']) != "" or (theCloud['password'] != "")):
                mqttClient.username_pw_set(theCloud['username'], theCloud['password'])

            if (cafile is not None):
                mqttClient.tls_set(ca_certs=cafile, certfile=clientCert, keyfile=clientKey)


            mqttClient.will_set(theCloud['lastWillTopic'], theCloud['lastWill'], 0)
            mqttClient.connect(theCloud['addr'], int(theCloud['port']), int(theCloud['keepAlive']))
            mqttClient.loop_start()

            cloudAddressStr = theCloud['addr'] + ":" + theCloud['port']
            ########END TODO
            log.info(("Cloud: %s" % theCloud))

            i = 0
            #Start New ones
            for coordinate in coordinates:
                worker = threadLoop.pollThread(str(i), json.dumps(coordinate), json.dumps(theCloud), mqttClient)
                log.info(("Starting Thread: %s" % coordinate))
                worker.start()
                runningListCoor.append(worker)
                i = i + 1

        else:
            log.info("Stopping polling")
            stopAll()

        return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

    if request.method == 'GET':
        pointsLoaded = len(runningListCoor) > 0
        log.info(("pointsLoaded on GET: %s" % pointsLoaded))
        return json.dumps({'success':True, 'started': pointsLoaded}), 200, {'ContentType':'application/json'}


@app.route('/ping', methods=['POST'])
def pingDev():

   if request.method == 'POST':
      ipToPing = request.get_json()
      log.info(("To Ping!: %s" % ipToPing))
      if (ping(ipToPing['ip'], ipToPing['port'])):
            return json.dumps({'success':True}), 200, {'ContentType':'application/json'}
      else:
            return json.dumps({'success':False}), 200, {'ContentType':'application/json'}

@app.route('/dash', methods=['GET'])
def dash():
    if not session.get('logged_in'):
       return render_template('login.html')

    cloudStatus = {"connected": flag_connected, "address": cloudAddressStr}
    pointsStatus = []

    for t in runningListCoor:
        item = t.SnmpResp
        pointsStatus.append(item)

    log.info(("pointsStatus: %s" % pointsStatus))
    log.info(("cloudStatus: %s" % cloudStatus))

    return render_template('dash.html', connected = cloudStatus, points = pointsStatus)



@app.route('/login', methods=['POST'])
def do_admin_login():
    userSession = request.form['username']
    session['logged_in'] = True
    return redirect(url_for('dash'))

@app.route("/logout")
def logout():
    session['logged_in'] = False
    return home()

if __name__ == "__main__":
   logging.basicConfig(level=logging.INFO, filename="SnmpMQTT.log")
   app.secret_key = os.urandom(12)
   conn = sqlite3.connect('database.db')
   conn.execute('CREATE TABLE IF NOT EXISTS devices (name TEXT, addr TEXT, port TEXT)')

   conn.execute("CREATE TABLE IF NOT EXISTS cloudProfile (addr TEXT, port TEXT,"
                "lastWill TEXT, lastWillTopic TEXT, username TEXT, password TEXT,"
                "clientCert TEXT, caFile TEXT, clientKey TEXT, clientId TEXT, keepAlive TEXT);")


   conn.execute("CREATE TABLE IF NOT EXISTS coordinates (oid TEXT, devName TEXT,"
                "snmpOper INTEGER, topic TEXT, interval TEXT, operEnum INTEGER,compare TEXT);")
   conn.commit()
   conn.close()

   log.info("Application Started")

   if not os.path.exists(certPath):
      os.mkdir(certPath)
      log.info("Created: " + certPath)
   app.run(debug=True,host='0.0.0.0', port=4000)
