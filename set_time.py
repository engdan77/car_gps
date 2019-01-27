import threading
from gps import *
import time
import calendar

class GpsPoller(threading.Thread):
    ''' Class that polls GPS in a thread'''
    def __init__(self):
        threading.Thread.__init__(self)
        #starting the stream of info
        self.gpsd = gps(mode=WATCH_ENABLE)
        self.current_value = None
        #setting the thread running to true
        self.running = True

    def run(self):
        while self.running:
            #this will continue to loop and grab EACH set
            # of gpsd info to clear the buffer
            self.gpsd.next()


def set_gps_time(objGPS, timeout=300):
    import datetime
    from time import strptime
    import os

    # For debug without GPS
    # return ('2014-01-13 08:01:56', 59.349638848, 17.99518279, 42.978, 0.523)

    objGPS.start()

    varFix = objGPS.gpsd.fix.mode

    duration = 0
    SLEEP = 2
    TIMEOUT = timeout / SLEEP

    while varFix == 1 and duration < TIMEOUT:
        varTime = objGPS.gpsd.utc
        if varTime is not None and varTime != '':
            # Convert time to DateTime
            try:
                varTime = strptime(varTime[0:19], '%Y-%m-%dT%H:%M:%S')
            except:
                return None
            else:
                # Convert DatTime to Epoch
                varTime = calendar.timegm(varTime)
                # Convert Epoch back to LocalTime
                varTime = datetime.datetime.fromtimestamp(varTime).strftime('%Y-%m-%d %H:%M:%S')

                # SET SYSTEM TIME
                gpstime = objGPS.gpsd.utc[0:4] + objGPS.gpsd.utc[5:7] + objGPS.gpsd.utc[8:10] + ' ' + objGPS.gpsd.utc[11:19]
                os.system('sudo date --set="%s"' % gpstime)

            varFix = objGPS.gpsd.fix.mode
            varLat = objGPS.gpsd.fix.latitude
            varLon = objGPS.gpsd.fix.longitude
            varAlt = objGPS.gpsd.fix.altitude
            varSpeed = objGPS.gpsd.fix.speed
            time.sleep(SLEEP)
            duration = duration + SLEEP

    objGPS.running = False

    if varFix == 1:
        return None
    else:
        return varTime, varLat, varLon, varAlt, varSpeed

objGps = GpsPoller()
result = set_gps_time(objGps, 300)
if result is None:
    time.sleep(120)
    result = set_gps_time(objGps, 300)


