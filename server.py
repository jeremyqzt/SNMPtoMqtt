from flask import Flask, flash, redirect, render_template, request, session, abort, url_for
import os
import json
import sqlite3
import socket
import threading
import threadLoop
import paho.mqtt.client as paho

runningListCoor = []
lock = threading.Lock()
userSession = ""

def ping(ip, port):
   s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   s.settimeout(1)
   try:
      s.connect((ip, int(port)))
      s.shutdown(2)
      return True
   except:
      return False

app = Flask(__name__)

@app.route('/')
def home():
   if not session.get('logged_in'):
      return render_template('login.html')
   else:
      return redirect(url_for('saveDev'))

@app.route('/saveCloud', methods=['POST', 'GET'])
def saveCloud():
   if not session.get('logged_in'):
      return render_template('login.html')

   if request.method == 'POST':
      data = request.get_json()
      sql = ' INSERT INTO cloudProfile(addr,port,lastWill,lastWillTopic,username,password,clientId,keepAlive) VALUES(?,?,?,?,?,?,?,?) '
      conn = sqlite3.connect('database.db')
      conn.execute('DELETE FROM cloudProfile;')
      conn.commit()
      conn.execute(sql, (data['cloudAddr'], data['cloudPort'], data['lastWillMessage'], data['lastWillTopic'],
                         data['username'],data['password'], data['clientId'],data['keepAlive']))

      conn.commit()
      return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

   if request.method == 'GET':
      conn = sqlite3.connect('database.db')
      conn.row_factory = sqlite3.Row
      cursor = conn.execute("SELECT * FROM cloudProfile;")
      rows = cursor.fetchall()
      cloudData = [dict(ix) for ix in rows]
      print(cloudData)
      conn.close()
      if (cloudData):
         return render_template('clouds.html', cloud=cloudData)
      else:
         return render_template('clouds.html', cloud=[])


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


        #TODO: Abstract this 1 level higher
        mqttClient= paho.Client(theCloud['clientId'])

        if ((theCloud['username']) != "" or (theCloud['password'] != "")):
            mqttClient.username_pw_set(theCloud['username'], theCloud['password'])


        mqttClient.will_set(theCloud['lastWillTopic'], theCloud['lastWill'], 0)
        mqttClient.connect(theCloud['addr'], int(theCloud['port']), int(theCloud['keepAlive']))

        ########END TODO
        
        i = 0
        #Kill Old Threads
        for pollThread in runningListCoor:
            pollThread.stopRunning()

        runningListCoor.clear()

        #Start New ones
        for coordinate in coordinates:
            print(i)
            worker = threadLoop.pollThread(str(i), json.dumps(coordinate), json.dumps(theCloud), mqttClient)
            worker.start()
            runningListCoor.append(worker)
            i = i + 1
        print(runningListCoor)

      else:
        print("got index wrong")

      return json.dumps({'success':True}), 200, {'ContentType':'application/json'}


@app.route('/ping', methods=['POST'])
def pingDev():
   if request.method == 'POST':
      ipToPing = request.get_json()
      if (ping(ipToPing['ip'], ipToPing['port'])):
            return json.dumps({'success':True}), 200, {'ContentType':'application/json'}
      else:
            return json.dumps({'success':False}), 200, {'ContentType':'application/json'}



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
                "caFile TEXT, clientKey TEXT, clientCert TEXT, clientId TEXT, keepAlive TEXT);")


   conn.execute("CREATE TABLE IF NOT EXISTS coordinates (oid TEXT, devName TEXT,"
                "snmpOper TEXT, topic TEXT, interval TEXT);")
   conn.commit()
   conn.close()

   app.run(debug=True,host='0.0.0.0', port=4000)
