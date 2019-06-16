from flask import Flask
from flask import Flask, flash, redirect, render_template, request, session, abort
import os
import json
import sqlite3
import socket

def ping(ip,port):
   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
   #if not session.get('logged_in'):
   #   return render_template('login.html')
   #else:
   conn = sqlite3.connect('database.db')
   conn.row_factory = sqlite3.Row
   cursor = conn.execute("SELECT * FROM devices;")
   rows = cursor.fetchall()
   dev = [dict(ix) for ix in rows]
   print(dev)
   conn.close()
  
   return render_template('devices.html', devices=dev)

@app.route('/saveDev', methods=['POST', 'GET'])
def saveDev():
   if request.method == 'POST':
      data = request.get_json()
      conn = sqlite3.connect('database.db')
      conn.execute('DELETE FROM devices;')
      sql = ' INSERT INTO devices(name,addr,port) VALUES(?,?,?) '
      for i in data:
            name = i['name']
            ip = i['ip']
            port = i['port']
            conn.execute(sql, (name, ip, port))
      conn.commit()
      conn.close()
      return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 
   if request.method == 'GET':
      return render_template('devices.html')

@app.route('/ping', methods=['POST'])
def pingDev():
   if request.method == 'POST':
      ipToPing = request.get_json()
      print(ipToPing)
      if (ping(ipToPing['ip'], ipToPing['port'])):
            return json.dumps({'success':True}), 200, {'ContentType':'application/json'}
      else:
            return json.dumps({'success':False}), 200, {'ContentType':'application/json'}
      


@app.route('/login', methods=['POST'])
def do_admin_login():
   print("Logging IN")
   if request.form['password'] == 'password' and request.form['username'] == 'admin':
      session['logged_in'] = True
      return render_template('devices.html')
   else:
      return render_template('login.html', error = 'Login Failed')

      
if __name__ == "__main__":
   app.secret_key = os.urandom(12)
   conn = sqlite3.connect('database.db')
   conn.execute('CREATE TABLE IF NOT EXISTS devices (name TEXT, addr TEXT, port TEXT)')
   conn.close()
   app.run(debug=True,host='0.0.0.0', port=4000)
