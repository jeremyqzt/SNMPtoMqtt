from flask import Flask, flash, redirect, render_template, request, session, abort, url_for
import os
from os.path import isfile, join
import json
import sqlite3
import socket
import threading
import threadLoop
import paho.mqtt.client as paho
from werkzeug import secure_filename
import ssl

certPath = "certs"
app = Flask(__name__)

runningListCoor = []
lock = threading.Lock()
userSession = ""
mqttClient = None
cloudAddressStr = "Unattempted"
flag_connected = "Unattempted"


def on_connect(client, userdata, flags, rc):
    print("Connected!")
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

    for pollThread in runningListCoor:
        pollThread.setRunning(False)

    for pollThread in runningListCoor:
        pollThread.join()

    runningListCoor.clear()
    if mqttClient is not None:
      mqttClient.disconnect()

    mqttClient = None

def ping(ip, port):
   s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   s.settimeout(1)
   try:
      s.connect((ip, int(port)))
      s.shutdown(2)
      return True
   except:
      return False

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
      print(data)
      conn.execute(sql, (data['cloudAddr'], data['cloudPort'], data['lastWillMessage'], data['lastWillTopic'],
                         data['username'],data['password'], data['clientId'],data['keepAlive'], data['clientCert'],data['caCert'],data['clientKey']))

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
      print(dev)
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
      sql = ' INSERT INTO coordinates(oid, devName ,snmpOper, topic, interval) VALUES(?,?,?,?,?) '
      for i in data:
            oid = i['oid'].strip()
            oper = i['oper'].strip()
            interval = i['interval'].strip()
            topic = i['topic'].strip()
            name = i['name'].strip()
            conn.execute(sql, (oid, name, oper, topic, interval))

      conn.commit()
      conn.close()

      return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

   if request.method == 'GET':
      conn = sqlite3.connect('database.db')
      conn.row_factory = sqlite3.Row
      cursor = conn.execute("SELECT * FROM devices;")
      rows = cursor.fetchall()
      dev = [dict(ix) for ix in rows]

      cursor = conn.execute("SELECT * FROM coordinates;")
      rows = cursor.fetchall()
      coordinates = [dict(ix) for ix in rows]

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


            i = 0
            #Start New ones
            for coordinate in coordinates:
                worker = threadLoop.pollThread(str(i), json.dumps(coordinate), json.dumps(theCloud), mqttClient)
                worker.start()
                runningListCoor.append(worker)
                i = i + 1

        else:
            stopAll()

        return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

    if request.method == 'GET':
        pointsLoaded = len(runningListCoor) > 0
        return json.dumps({'success':True, 'started': pointsLoaded}), 200, {'ContentType':'application/json'}


@app.route('/ping', methods=['POST'])
def pingDev():
   if request.method == 'POST':
      ipToPing = request.get_json()
      if (ping(ipToPing['ip'], ipToPing['port'])):
            return json.dumps({'success':True}), 200, {'ContentType':'application/json'}
      else:
            return json.dumps({'success':False}), 200, {'ContentType':'application/json'}

@app.route('/dash', methods=['GET'])
def dashboard():
    if not session.get('logged_in'):
       return render_template('login.html')

    cloudStatus = {"connected": flag_connected, "address": cloudAddressStr}

    return render_template('dash.html', connected = cloudStatus)



@app.route('/login', methods=['POST'])
def do_admin_login():
   userSession = request.form['username']
   session['logged_in'] = True
   return redirect(url_for('saveDev'))

if __name__ == "__main__":
   app.secret_key = os.urandom(12)
   conn = sqlite3.connect('database.db')
   conn.execute('CREATE TABLE IF NOT EXISTS devices (name TEXT, addr TEXT, port TEXT)')

   conn.execute("CREATE TABLE IF NOT EXISTS cloudProfile (addr TEXT, port TEXT,"
                "lastWill TEXT, lastWillTopic TEXT, username TEXT, password TEXT,"
                "clientCert TEXT, caFile TEXT, clientKey TEXT, clientId TEXT, keepAlive TEXT);")


   conn.execute("CREATE TABLE IF NOT EXISTS coordinates (oid TEXT, devName TEXT,"
                "snmpOper TEXT, topic TEXT, interval TEXT);")
   conn.commit()
   conn.close()
   
   if not os.path.exists(certPath):
      os.mkdir(certPath)
   app.run(debug=True,host='0.0.0.0', port=4000)
