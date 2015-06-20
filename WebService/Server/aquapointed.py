#!/usr/bin/env python
#
# Christopher Harding
# CS482
# 10/30/14
#

import os
import zipfile
import sys
import signal
import sqlite3
import serial
import uuid
import csv
import datetime
import socket

from sets import Set
from daemon import Daemon
from subprocess import call
from subprocess import check_output
from twisted.python import log
from twisted.internet.defer import inlineCallbacks
from autobahn import wamp
from autobahn.twisted.util import sleep
from autobahn.twisted.wamp import ApplicationSession

## Configuration Constants
##
POLLING_INTERVAL = 1 # In seconds
DATA_FILE = '/usr/local/AquaPointe/data/data.db'
CONFIG_FILE = '/usr/local/AquaPointe/config/config.db'
PID_FILE = '/var/run/aquapointe.pid'
LOG_FILE = '/var/log/aquapointe.log'
WEB_DIRECTORY = '/root'
DOWNLOAD_DIRECTORY = '/root/downloads/'
SERIAL_PORT = '/dev/ttyATH0'
BAUD_RATE = 9600
WEB_PORT = 80
MAX_DATABASE_RECORDS = 1000


class APComponent(ApplicationSession):
    """
    Main functionality of the server application.
    """
    
    def __init__(self, config = None):
        """
        Constructor.
        """
        conn = sqlite3.connect(CONFIG_FILE)
        cur = conn.cursor()

        cur.execute("""SELECT value FROM Frequency""")
        row = cur.fetchone()
        
        if row != None:
            frequency = row[0]
            if frequency == 0:
                self.delta = datetime.timedelta(days=1)
            elif frequency == 1:
                self.delta = datetime.timedelta(hours=1)
            elif frequency == 2:
                self.delta = datetime.timedelta(minutes=1)
        else:
            ## If a measurement is not found, default to hours
            self.delta = datetime.timedelta(hours=1)
     
        conn.close()
        
        self.networkDevices = [socket.gethostname() + ".local"]
        ApplicationSession.__init__(self, config)
        

    @inlineCallbacks
    def onJoin(self, details):
        """
        This method is called when the system starts up.
        """
        ## Register procedures for remote calling
        ##            
        yield self.register(self)
        
        serialConnection = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        
        ## Counter used to insert values into the database every hour
        ##
        currentTime = datetime.datetime.now()
        
        # This is so that there is a row in the database right away.
        currentTime = currentTime - self.delta
        
        # Polling for the network devices can't run everytime through the loop, so we count and only do it every 10 times
        counter = 0

        while True:
            # Interface from the Arduino side of the system. Writing the following
            # values to the serial allows reading the value back out.           
            # 1 = pH
            # 2 = Salinity
            # 3 = Temperature
            # 4 = PAR
            # 5 = Pump Movement
            # 6 = Test
            
            if serialConnection.isOpen():
                serialConnection.write("1\n")
                ph = serialConnection.readline().rstrip()

                serialConnection.write("2\n")
                temp = serialConnection.readline().rstrip()

                serialConnection.write("3\n")
                sal = serialConnection.readline().rstrip()

                serialConnection.write("4\n")
                par = serialConnection.readline().rstrip()

                serialConnection.write("5\n")
                flowValue = str(serialConnection.readline().rstrip())

                if flowValue == 'True':
                    flow = 1
                else:
                    flow = 0

                payload = {u'ph': ph, u'temp': temp, u'sal': sal, u'par': par, u'flow': flow}
                self.publish(u'com.aquapointe.ondata', payload)
                
                ## Store the measurements in the database every hour
                ##
                if datetime.datetime.now() >= currentTime + self.delta:
                    currentTime = datetime.datetime.now()
                    self.insertMeasurement(temp, sal, par, ph, flow)
            
            ## This section polls for changes to the network and sends them out to the client.
            ##
            if counter > 9:
                networkList = [socket.gethostname() + ".local"]       
                rawNetworkData = check_output(["avahi-browse", "-tlr", "_aquapointe._tcp"])
                words = rawNetworkData.split()
                for item in words:
                    if ".local" in item:
                        s = item.replace('[', '')
                        s = s.replace(']', '')
                        if s not in networkList:
                            networkList.append(s)
                self.publish(u'com.aquapointe.onnewhost', networkList)
                counter = 0
            else:
                counter += 1
                    
            yield sleep(POLLING_INTERVAL)           
    
        
    def insertMeasurement(self, temp, salinity, par, ph, flow):
        """
        Helper method to insert measurements into the sqlite database
        """
        ## Create a connection to the database
        ##
        conn = sqlite3.connect(DATA_FILE)
        cur = conn.cursor()
        
        ## Create the table if it does not exist
        ##
        cur.execute("""CREATE TABLE IF NOT EXISTS measurements
                    (timestamp TEXT NOT NULL, temperature TEXT NOT NULL, 
                    salinity TEXT NOT NULL, par TEXT NOT NULL, ph TEXT NOT NULL, 
                    flow INTEGER NOT NULL)
                    """)
                    
        conn.commit()
        
        ## Insert the measurement data into the database
        ##
        cur.execute("""INSERT INTO measurements VALUES (DATETIME('now'),?,?,?,?,?)""", (temp, salinity, par, ph, flow))
        
        
        ## Since this is used in an embedded environment, the file size needs to be kept small.
        ##
        cur.execute("""DELETE FROM measurements WHERE timestamp IN 
                       (SELECT timestamp FROM measurements ORDER BY timestamp ASC LIMIT 
                        (SELECT (CASE WHEN COUNT(*) - ? < 0 
                                      THEN 0 
                                      ELSE COUNT(*) - ? 
                                      END) FROM measurements))
                    """, (MAX_DATABASE_RECORDS, MAX_DATABASE_RECORDS))
        conn.commit()
        cur.execute("""VACUUM""")
        
        ## Close the connection
        ##
        conn.close()
        log.msg("Measurements saved in the database")
        
        ## Clean up the logins table
        ##
        conn = sqlite3.connect(CONFIG_FILE)
        cur = conn.cursor()

        cur.execute("""DELETE FROM Logins WHERE timestamp < DATETIME('now','-1 day')""")
        conn.commit()
        conn.close()
        log.msg("Logins table cleaned")
        
        ## Clean up the downloads directory
        ##
        log.msg("Downloads directory cleaned")
        os.chdir(DOWNLOAD_DIRECTORY)
        fileList = os.listdir(os.getcwd())
        for fn in fileList: 
            os.remove(os.path.join(os.getcwd(), fn))
        
    
    @wamp.register(u'com.aquapointe.login')    
    def doLogin(self, args):
        """
        This method is exported as RPC and can be called by connected clients
        """
        username = ""
        password = ""
        if args[0] is not None and args[1] is not None:
            username = args[0].lower()
            password = args[1]
        else:
            return "null"
            
        ## Do the actual checking of the password
        log.msg("Attempted login by:", username)     
        conn = sqlite3.connect(CONFIG_FILE)
        cur = conn.cursor()

        cur.execute("SELECT password FROM Users WHERE username=?", [(username)])
        row = cur.fetchone()
        
        if row is None:
            log.msg("Failed login by:", username, "Account does not exist")
            conn.close()
            return "null"
            
        if row[0] == password:
            log.msg("Successful login by:", username)
            sessionID = str(uuid.uuid4())
            cur.execute("""INSERT INTO Logins VALUES (DATETIME('now'),?)""", [(sessionID)])
            conn.commit()
            conn.close()
            return sessionID
        else:
            log.msg("Failed login by:", username, "Password does not match what was stored")
            conn.close()
            return "null"
            
    @wamp.register(u'com.aquapointe.changepassword')    
    def changePassword(self, username, oldPass, newPass):
        """
        This method is exported as RPC and can be called by connected clients
        """
         ## Do the actual checking of the password
        log.msg("Attempted password change by:", username)     
        conn = sqlite3.connect(CONFIG_FILE)
        cur = conn.cursor()

        cur.execute("SELECT password FROM Users WHERE username=?", [(username)])
        row = cur.fetchone()
        
        if row is None:
            log.msg("Failed password change by:", username, "Account does not exist")
            conn.close()
            return False
            
        if row[0] == oldPass:
            cur.execute("""UPDATE Users SET password = ? WHERE username = ?""", (newPass, username))
            conn.commit()
            conn.close()
            log.msg("Successful password change by:", username)
            return True
        else:
            log.msg("Failed password change by:", username, "Password does not match what was stored")
            conn.close()
            return False
        
    @wamp.register(u'com.aquapointe.validate')    
    def validateToken(self, token):
        """
        This method is exported as RPC and can be called by connected clients
        """
        conn = sqlite3.connect(CONFIG_FILE)
        cur = conn.cursor()

        cur.execute("""SELECT COUNT(*) FROM Logins WHERE uuid=?""", [(token)])
        row = cur.fetchone()
        
        if row[0] > 0:
            log.msg("Valid Session ID")
            conn.close()
            return True
        else:
            log.msg("Invalid Session ID") 
            conn.close()
            return False
            
    @wamp.register(u'com.aquapointe.setdescription')    
    def setDescription(self, description):
        """
        This method is exported as RPC and can be called by connected clients
        """
        conn = sqlite3.connect(CONFIG_FILE)
        cur = conn.cursor()

        cur.execute("""DELETE FROM Description""")
        conn.commit()
        cur.execute("""INSERT INTO Description VALUES (?)""", [(description)])
        conn.commit()
        conn.close()
        log.msg("Device description changed to:", description)
        return True
    
    @wamp.register(u'com.aquapointe.getdescription')    
    def getDescription(self):
        """
        This method is exported as RPC and can be called by connected clients
        """
        result = None
         
        conn = sqlite3.connect(CONFIG_FILE)
        cur = conn.cursor()
  
        cur.execute("""SELECT value FROM Description""")
        row = cur.fetchone()
         
        if row is not None:
            result = row[0]
        else:
            result = "No Name"
             
        conn.close()
        return result 
        
    @wamp.register(u'com.aquapointe.rename')    
    def setHostName(self, name):
        """
        This method is exported as RPC and can be called by connected clients
        """
        if (name is not None):
            call(["uci", "set", "system.@system[0].hostname="+name])
            call(["uci", "commit", "system"])
            log.msg("Device Host Name changed to:", name)
            call(["reboot"])
            return True
        else:
            log.msg("Device Host Name change failed")
            return False
            
    @wamp.register(u'com.aquapointe.gethostname')    
    def getHostName(self):
        """
        This method is exported as RPC and can be called by connected clients
        """
        return socket.gethostname()
        
    @wamp.register(u'com.aquapointe.getdevicelist')    
    def getDeviceList(self):
        """
        This method is exported as RPC and can be called by connected clients
        """
        results = [socket.gethostname() + ".local"]       
        rawNetworkData = check_output(["avahi-browse", "-tlr", "_aquapointe._tcp"])
        words = rawNetworkData.split()
        for item in words:
            if ".local" in item:
                s = item.replace('[', '')
                s = s.replace(']', '')
                if s not in results:
                    results.append(s)
        return  results
        
    @wamp.register(u'com.aquapointe.setfrequency')    
    def setFrequency(self, frequency):
        """
        This method is exported as RPC and can be called by connected clients
        """
        conn = sqlite3.connect(CONFIG_FILE)
        cur = conn.cursor()

        cur.execute("""DELETE FROM Frequency""")
        conn.commit()
        cur.execute("""INSERT INTO Frequency VALUES (?)""", [(frequency)])
        conn.commit()
        conn.close()
        
        if frequency == 0:
            self.delta = datetime.timedelta(days=1)
        elif frequency == 1:
            self.delta = datetime.timedelta(hours=1)
        elif frequency == 2:
            self.delta = datetime.timedelta(minutes=1)
            
        log.msg("Device measurement frequency changed to:", self.delta)
        return True
        
    @wamp.register(u'com.aquapointe.getdevicesettings')    
    def getDeviceSettings(self):
        """
        This method is exported as RPC and can be called by connected clients
        """
        results = []
        
        conn = sqlite3.connect(CONFIG_FILE)
        cur = conn.cursor()

        cur.execute("""SELECT value FROM Description""")
        row = cur.fetchone()
        
        if row is not None:
            results.append(row[0])
        else:
            results.append("No Name")
            
        cur.execute("""SELECT value FROM Frequency""")
        row = cur.fetchone()
        
        if row is not None:
            results.append(row[0])
        else:
            results.append(0)
            
        conn.close()
        return results
        
    @wamp.register(u'com.aquapointe.configurenetwork')    
    def configureNetwork(self, networkName, password):
        """
        This method is exported as RPC and can be called by connected clients
        """
        call(["/sbin/uci", "set", "wireless.@wifi-iface[0].ssid="+networkName])
        call(["/sbin/uci", "set", "wireless.@wifi-iface[0].key="+password])
        call(["/sbin/uci", "commit", "wireless"])
        call(["/etc/init.d/network", "reload"])
        log.msg("Wireless network SSID changed to:", networkName);
        return True
    
    @wamp.register(u'com.aquapointe.getnetworksettings')    
    def getNetworkSettings(self):
        """
        This method is exported as RPC and can be called by connected clients
        """
        results = []
        hostName = socket.gethostname()
        results.append(hostName)
        ssid = check_output(["/sbin/uci", "get", "wireless.@wifi-iface[0].ssid"])
        results.append(ssid)
        
        return results         
            
    @wamp.register(u'com.aquapointe.downloadcsv')    
    def downloadCSV(self):
        """
        This method is exported as RPC and can be called by connected clients
        """
        conn = sqlite3.connect(DATA_FILE)
        cur = conn.cursor()

        cur.execute("""SELECT datetime(timestamp, 'localtime') as Timestamp, 
                                temperature AS Temperature, 
                                salinity as Salinity, 
                                par as PAR, 
                                ph as pH,
                                CASE flow WHEN 0 THEN 'Off' WHEN 1 THEN 'On' END as Flow 
                                FROM measurements ORDER BY timestamp""")
        
        timestamp = datetime.datetime.now()
        filename = "Data " + timestamp.strftime('%b %d %Y %H:%M:%S')
        csvFilename = filename + '.csv'
        zipFilename = filename + '.zip'
        csv_path = DOWNLOAD_DIRECTORY + csvFilename
        zip_path = DOWNLOAD_DIRECTORY + zipFilename
        with open(csv_path, "wb") as csv_file:
            csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_MINIMAL)
            # Write headers.
            csv_writer.writerow([i[0] for i in cur.description])
            # Write data.
            csv_writer.writerows(cur)
        
        zf = zipfile.ZipFile(zip_path, mode='w')
        zf.write(csv_path, csvFilename)
        zf.close()
        os.remove(csv_path)
        conn.close()
        log.msg("CSV download file generated")
        return zipFilename


## This Class startups up the webservice and represents the running process.
##            
class APProcess(Daemon):
    """
    This class encapsulates the running WebService process.
    """ 
    def handler(self, signum = None, frame = None):
        """A signal handler for the daemon."""
        self.delpid()
        sys.exit(0)

    ## Overridden from Daemon
    ##
    def run(self):
        for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT]:
            signal.signal(sig, self.handler)
        
        ## Start logging to logfile
        ##
        log.startLogging(open(LOG_FILE, 'w'))

        ## create embedded web server for static files
        ##
        from twisted.internet import reactor
        log.msg("Using Twisted reactor {0}".format(reactor.__class__))

        from twisted.web.server import Site
        from twisted.web.static import File
        reactor.listenTCP(WEB_PORT, Site(File(WEB_DIRECTORY)))

        ## run WAMP application component
        ##
        from autobahn.twisted.wamp import ApplicationRunner
        runner = ApplicationRunner('ws://localhost:8080', u"realm1", None, None, True)

        ## start the component and the Twisted reactor ..
        ##
        runner.run(APComponent) 
            
    ## Overridden from Daemon
    ##
    def stop(self):
        Daemon.stop(self)
        

## Main entry point of the script. This starts the process and goes through the procedures to get a proper daemon up and running
##
if __name__ == "__main__":
    
    ## parse command line arguments
    ##
    daemon = APProcess(PID_FILE)
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
    