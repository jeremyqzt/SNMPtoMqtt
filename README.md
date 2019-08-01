# SNMP to MQTT
This project is an attempt to build an application to poll SNMP devices and convert the result into MQTT

### Prerequisites

to run, you'll need
```
#python3+
apt-get install python3.5

#python packages
pip install -r requirements.txt

```
### run the application on localhost:4000
```
python3.5 server.py
```
### TODOs
```
Make the user accounts mutual exclusive - Only 1 account at a time
Test SSL/TLS
Improve Error Reporting
Improve Ui consistency
Logging mechanism (use syslog?)
Remove print messages
Logout to End session
Conditional publishing
```
