#!/usr/bin/env python

import os
import sys
from gps import *
import time
import threading
from edo import *
import threading

global sync_counter
sync_counter = "None"
global sync_complete
sync_complete = "False"

# Kivy specific
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.properties import DictProperty, ObjectProperty, StringProperty
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.app import App
from functools import partial

__version__ = "$Revision: 20140903.538 $"


SYNC_IP = 'ip_to_server'
SYNC_USER = 'username_for_db'
SYNC_PASS = 'pass_for_db'
SYNC_DBNAME = 'cargps'
YOUTUBE_URL = 'http://www.youtube.com/watch?v='
YOUTUBE_ENABLE = False
CHECK_IP = 'www.abc.se'
CHECK_PORT = 80
SONG = 'edo.ogg'


# Setting the global variable
gpsd = None


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


def edoGetCoord(objGPS, timeout=300):
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


def createDB(objFile, logObject):
        ''' Creates database if necessary '''
        try:
            f = open(objFile)
        except:
            oDB = edoClassDB('sqlite', objFile, logObject)
            ## oDB=edoClassDB('mysql',('192.168.200.130','3306','user','pass','test')
            oDB.create((['cargps', 'time', 'TEXT'],
                        ['cargps', 'lat', 'TEXT'],
                        ['cargps', 'lon', 'TEXT'],
                        ['cargps', 'alt', 'TEXT'],
                        ['cargps', 'speed', 'TEXT'],
                        ['cargps', 'tripno', 'INTEGER'],
                        ['cargps', 'seq', 'INTEGER'],
                        ['cargps', 'dist', 'INTEGER'],
                        ['cargps', 'sync', 'TEXT']))
            # Insert initial record
            oDB.insert('cargps', {'time': '2014-01-01 00:00:00',
                                    'lat': '59.349000000',
                                    'lon': '17.99500000',
                                    'alt': '0',
                                    'speed': '0',
                                    'tripno': '0',
                                    'seq': '1',
                                    'dist': '0',
                                    'sync': '2014-01-01 00:00:00'})
        else:
            f.close()
            oDB = edoClassDB('sqlite', objFile, logObject)
        return oDB


def createSyncDB(db_ip, db_user, db_pass, db_name, logObject):
        ''' Creates sync-database if necessary '''
        if edoTestSocket(db_ip, 3306, logObject) == 0:
            oDB = edoClassDB('mysql', (db_ip, '3306', db_user, db_pass, db_name), logObject)
            oDB.create((['cargps', 'time', 'TEXT'],
                        ['cargps', 'lat', 'TEXT'],
                        ['cargps', 'lon', 'TEXT'],
                        ['cargps', 'alt', 'TEXT'],
                        ['cargps', 'speed', 'TEXT'],
                        ['cargps', 'tripno', 'INTEGER'],
                        ['cargps', 'seq', 'INTEGER'],
                        ['cargps', 'dist', 'INTEGER'],
                        ['cargps', 'sync', 'TEXT']))
            return oDB
        else:
            return None


def getDistToday(objDB):
    ''' Get todays distance stored in database '''
    import time
    dist = time.strftime("%Y-%m-%d")

    dist = objDB.sql('SELECT sum(dist) FROM cargps WHERE time LIKE "' + str(dist) + '%"')[0][0]
    if dist > 0:
        # tot = "%.1f" % dist
        return dist
    else:
        return 0


def getDistBetween(objDB, start_date, end_date):
    ''' Get todays distance stored in database '''

    dist = objDB.sql('SELECT sum(dist) FROM cargps WHERE time BETWEEN "' + start_date + '" AND "' + end_date + '"')[0][0]
    if dist > 0:
        return round(dist)
    else:
        return 0


def getNextTrip(objDB):
    ''' Get the last TripNo stored in database '''
    trip = objDB.sql('SELECT max(tripno) FROM cargps')[0][0]
    if trip is None:
        return 1
    else:
        return int(trip) + 1


def getCurrentTrip(objDB):
    ''' Get the last TripNo stored in database '''
    trip = int(objDB.sql('SELECT max(tripno) FROM cargps')[0][0])
    if trip is None:
        return 1
    else:
        return trip


def getNextSeq(objDB, trip):
    ''' Get next sequence for trip '''
    seq = objDB.sql('SELECT max(seq) FROM cargps WHERE tripno = ' + str(trip))[0][0]
    if seq is None:
        return 1
    else:
        return int(seq) + 1


def getLastCoord(objDB):
    ''' Get the last coordinates '''
    return objDB.sql('SELECT * from cargps ORDER BY id DESC LIMIT 1')[0]


def getDist(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    from math import radians, cos, sin, asin, sqrt
    lon1 = float(lon1)
    lat1 = float(lat1)
    lon2 = float(lon2)
    lat2 = float(lat2)

    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    km = 6367 * c
    return km * 1000


def insertGps(objDB, tripno, *args):
    ''' Inserts GPS data to database '''
    # Check if any coordinates in the past
    lastTrip = getLastCoord(objDB)[6]
    if lastTrip == tripno:
        lastLat = getLastCoord(objDB)[2]
        lastLon = getLastCoord(objDB)[3]
        # Present coordinates
        curLat = args[1]
        curLon = args[2]
        # Get distance betwen
        dist = getDist(lastLon, lastLat, curLon, curLat)
    else:
        dist = 0.0

    # Get next sequence
    seq = getNextSeq(objDB, tripno)

    objDB.insert('cargps', {'time': args[0],
                            'lat': args[1],
                            'lon': args[2],
                            'alt': args[3],
                            'speed': args[4],
                            'tripno': tripno,
                            'seq': seq,
                            'dist': round(dist),
                            'sync': 'null'})


def getRandomYoutubeURL(argURL):
    ''' Get id of most popular youtube videos '''
    import re
    import random
    import urllib2
    import sys

    # Get content
    html = urllib2.urlopen(argURL).read()

    # Get youtube links
    # f = open('./popular.html', 'rb')
    # html = f.read()

    all_tags = re.findall('watch\?v=(\w+)&', html)
    # print("html: ")
    # print html
    # print("all_tags: ")
    # print all_tags
    # sys.exit(0)
    if len(all_tags) > 0:
        random_num = random.randrange(1, len(all_tags))
        return all_tags[random_num]
    else:
        return "lksc2WRUOdM"


class mplayer:
    ''' Class for start and stop playing mp3 '''
    def __init__(self, song):
        self.song = song

    def start(self):
        import subprocess
        import os
        os.system("killall -9 mplayer")
        os.system("killall -9 /bin/sh")
        self.player = subprocess.Popen(["/bin/sh", "-c", "mplayer -loop 0 " + SONG], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def stop(self):
        self.player.stdin.write("q")

    def status(self):
        return self.status


Builder.load_string('''
<rootWidget>
    BoxLayout:
        orientation: 'vertical'
        Label:
            id: label_coord
            size_hint_y: None
            text: 'Lat: ' + str(root.infoDict['lat']) + ' Lon: ' + str(root.infoDict['lon'])
            font_size: 30
            height: 50
            canvas:
                Color:
                    rgba: 0, 1, 0, 0.5
                Rectangle:
                    pos: self.pos
                    size: self.size
        BoxLayout:
            orientation: 'horizontal'
            Label:
                size_hint_x: 0.1
            BoxLayout:
                orientation: 'vertical'
                Label:
                    size_hint_x: None
                    markup: True
                    text: 'Idag: [color=FF9CB3]' + str(root.infoDict['today']) + '[/color]'
                    font_size: 20
                Label:
                    size_hint_x: None
                    text: 'Jan: ' + str(root.infoDict['jan'])
                    font_size: 20
                Label:
                    size_hint_x: None
                    text: 'Feb: ' + str(root.infoDict['feb'])
                    font_size: 20
                Label:
                    size_hint_x: None
                    text: 'Mar: ' + str(root.infoDict['mar'])
                    font_size: 20
                Label:
                    size_hint_x: None
                    text: 'Apr: ' + str(root.infoDict['apr'])
                    font_size: 20
                Label:
                    size_hint_x: None
                    text: 'Maj: ' + str(root.infoDict['may'])
                    font_size: 20
                Label:
                    size_hint_x: None
                    text: 'Jun: ' + str(root.infoDict['jun'])
                    font_size: 20
                Label:
                    size_hint_x: None
                    text: 'Jul: ' + str(root.infoDict['jul'])
                    font_size: 20
                Label:
                    size_hint_x: None
                    text: 'Aug: ' + str(root.infoDict['aug'])
                    font_size: 20
                Label:
                    size_hint_x: None
                    text: 'Sep: ' + str(root.infoDict['sep'])
                    font_size: 20
                Label:
                    size_hint_x: None
                    text: 'Okt: ' + str(root.infoDict['oct'])
                    font_size: 20
                Label:
                    size_hint_x: None
                    text: 'Nov: ' + str(root.infoDict['nov'])
                    font_size: 20
                Label:
                    size_hint_x: None
                    text: 'Dec: ' + str(root.infoDict['dec'])
                    font_size: 20
                Label:
                    size_hint_x: None
                    markup: True
                    text: 'Tot: [color=F2FA00]' + str(root.infoDict['tot']) + '[/color]'
                    font_size: 20
                Label:
                    size_hint_x: None
                    font_size: 20
                Button:
                    id: btn_youtube
                    text: "youtube"
                    size_hint_x: None
                    on_release: root.playYoutube()
                Button:
                    id: btn_quit
                    text: "Avsluta"
                    size_hint_x: None
                    on_release: root.quit_callback()
                BoxLayout:
                    orientation: 'vertical'
                    Label:
                        id: info
                        text: "Startar upp..."
                        font_size: 30
                        size_hint_y: None
                    Label:
                        size_hint_y: None
                    Label:
                        size_hint_y: None
                    Label:
                        text: 'EdoCarGps  ver:' + root.infoDict['ver']
                        font_size: 20
                        size_hint_y: None
''')


class rootWidget(BoxLayout):
    infoDict = DictProperty({'ver': __version__.split(":")[1], 'lat': '0', 'lon': '0', 'speed': '0', 'today': '', 'tot': '', 'jan': '', 'feb': '', 'mar': '', 'apr': '', 'may': '', 'jun': '', 'jul': '', 'aug': '', 'sep': '', 'oct': '', 'nov': '', 'dec': ''})
    optDict = DictProperty()

    def __init__(self, **kwargs):
        # Superclass if we like to adjust present init
        super(rootWidget, self).__init__(**kwargs)

        # Example expose kv object to python
        # self.objQuit = self.ids['btn_quit']

        # Example adding button with callback
        # self.btn = Button(text='hoo')
        # self.btn.bind(on_press=self.quit_callback)
        # self.add_widget(self.btn)

        # Used to update labell
        self.info_label = self.ids['info']

        # Used for check when last sync
        self.last_sync = 0
        # Used to check when youtube last was played
        self.last_youtube = 600
        # Used to check for how long driven slowly, set 600 so it will
        # initially start youtube, next after that once every 10 minute
        self.slow_period = 0

        # Create log object
        self.logObject = edoClassFileLogger('edoCarGps.log', 1, 5, 'DEBUG')
        # Create DB if needed
        self.objDB = createDB('edoCarGps.sqlite', self.logObject)

        # Get today year
        self.thisYear = edoGetDateTime().split('-')[0]

        # Get distance driven today
        self.infoDict['today'] = round(getDistToday(self.objDB) / 1000)
        # Get total
        self.infoDict['tot'] = round(getDistBetween(self.objDB, self.thisYear + '-01-01 00:00:00', str(int(self.thisYear) + 1) + '-01-01 00:00:00') / 1000)

        # Add driven km for all months this year
        for monthName, monthNum in (['jan', '01'], ['feb', '02'], ['mar', '03'], ['apr', '04'], ['may', '05'], ['jun', '06'], ['jul', '07'], ['aug', '08'], ['sep', '09'], ['oct', '10'], ['nov', '11'], ['dec', '12']):
            if monthName == 'dec':
                self.infoDict[monthName] = round(getDistBetween(self.objDB, self.thisYear + '-' + monthNum + '-' + '01' + '00:00:00', str(int(self.thisYear) + 1) + '-' + str(int(monthNum) + 1).zfill(2) + '-' + '01' + '00:00:00') / 1000)
            else:
                self.infoDict[monthName] = round(getDistBetween(self.objDB, self.thisYear + '-' + monthNum + '-' + '01' + '00:00:00', self.thisYear + '-' + str(int(monthNum) + 1).zfill(2) + '-' + '01' + '00:00:00') / 1000)

        # Starting by get the next trip in local database
        self.tripno = getNextTrip(self.objDB)
        self.logObject.log("Starting new Trip: " + str(self.tripno), 'INFO')

        # Create song object playing mp3
        # self.bgsong = edoProcess("/bin/sh", "-c", "while true; do omxplayer " + SONG + " ; done")
        # self.logObject.log("Start playing background with pid: " + str(self.bgsong.pid), 'INFO')

    def update(self, objSync, dt):
        import time
        # Retrieve GPS
        objGPS = GpsPoller()
        # objGPS = None
        gpsTime, self.infoDict['lat'], self.infoDict['lon'], alt, self.infoDict['speed'] = edoGetCoord(objGPS, 300)

        # Get distance driven today
        self.infoDict['today'] = round(getDistToday(self.objDB) / 1000)

        # Update info
        if self.last_youtube > 600 and self.slow_period > 12 and int(self.infoDict['speed']) <= 3 and YOUTUBE_ENABLE is True:
            self.info_label.text = str((18 - self.slow_period) * 10) + ' sek. kvar\ntill youtube video\nom du kor langsamt'
            self.logObject.log("Remaining seconds before play youtube: " + str((18 - self.slow_period) * 10), 'INFO')
        else:
            self.info_label.text = 'Hastighet ' + str(round(int(self.infoDict['speed']) * 3.6)) + 'km/h'
            # If sync is in progress
            if objSync[0] != "None" and objSync[1] == "False":
                self.info_label.text = "Synkroniserar rutter " + objSync[0]
                print "Sync record: " + str(objSync[0])

        # Add present trip-data to local database
        insertGps(self.objDB, self.tripno, gpsTime, self.infoDict['lat'], self.infoDict['lon'], alt, self.infoDict['speed'])


        # Check if playing youtube
        if self.last_youtube > 600 and self.slow_period > 18 and int(self.infoDict['speed']) <= 3 and YOUTUBE_ENABLE is True:
            ## self.logObject.log("Killing song with pid: " + str(self.bgsong.pid), 'INFO')
            ## self.bgsong.kill()
            self.info_label.text = "Spelar youtube video"
            self.playYoutube()
            ## self.bgsong = edoProcess("/bin/sh", "-c", "while true; do omxplayer " + SONG + " ; done")
            ## self.logObject.log("Start playing background with pid: " + str(self.bgsong.pid), 'INFO')
            self.last_youtube = 0
            self.slow_period = 0
        self.last_youtube = self.last_youtube + 1
        self.slow_period = self.slow_period + 1

        # Reset slow timer if speed exceeds
        if int(self.infoDict['speed']) > 4:
            self.slow_period = 0


    def checkSyncYoutube(self, *args):
        # Check if sync is required
        self.logObject.log("MAIN :" + sync_counter, 'INFO')
        if (self.last_sync == 0 or self.last_sync > 10) and args[0][1] == "False":
            self.logObject.log("Not synced, and driving for more than 5 minutes, will check if sync db works", 'INFO')
            if edoPing("qnap.engvalls.eu") == 0 and args[0][0] == "None":
                self.info_label.text = "Synkroniserar GPS till server"
                if sync_counter == "None":
                    self.info_label.text = "Synk start"
                    result = self.bgSyncClass(self.objDB, args[0], self.logObject)
                    result.start()
            if YOUTUBE_ENABLE is True and edoTestSocket(CHECK_IP, CHECK_PORT, self.logObject) == 0:
                self.logObject.log("Will attempt to download youtube video", 'INFO')
                self.info_label.text = "Laddar ned ny Youtube-video"
                self.downloadYoutube()
                self.logObject.log("Completed download youtube video", 'INFO')
            # If driven more than 3 km shutdown when arrive home
            # if self.infoDict['today'] > 3:
                # time.sleep(300)
                # os.system("sudo shutdown -h now")

        # For debug
        # print "self sync: " + str(self.last_sync)
        # print "today dist: " + str(self.infoDict['today'])
        # print "last youtube: " + str(self.last_youtube)
        # print "slow period: " + str(self.slow_period)
        # print "sync_counter: " + sync_counter
        # print "sync_complete: " + sync_complete

    def quit_callback(self):
        print("Avsluta")
        sys.exit(0)

    def downloadYoutube(self):
        ''' Download new youtube '''
        import pexpect

        if edoTestSocket(CHECK_IP, CHECK_PORT, self.logObject) == 0:
            URL = "http://m.youtube.com/channel/HC4qRk91tndwg?&desktop_uri=%2Fchannel%2FHC4qRk91tndwg"
            try:
                os.remove('./youtube.tmp')
            except OSError:
                pass
            youtubeId = getRandomYoutubeURL(URL)
            self.logObject.log('Start downloading ' + YOUTUBE_URL + youtubeId, 'INFO')
            expObj = edoExpect('./youtube-dl.py ' + YOUTUBE_URL + youtubeId + ' -o youtube.tmp', 300, self.logObject)
            result = expObj.expect(['100\%', pexpect.TIMEOUT, pexpect.EOF])
            if result[0] == 0:
                self.logObject.log('Successfully downloaded youtube.mp4', 'INFO')
                os.rename('./youtube.tmp', './youtube.mp4')
                self.logObject.log('Renamed youtube file.mp4', 'INFO')
                return 0
            else:
                self.logObject.log('Fail download', 'WARNING')
                return 1

    def playYoutube(self):
        ''' Play YouTube '''
        import pexpect

        if self.downloadYoutube() == 0:
            self.logObject.log('Playing new video', 'INFO')
            expObj = edoExpect('omxplayer youtube.mp4', 3600, self.logObject)
            result = expObj.expect([pexpect.TIMEOUT, pexpect.EOF])
        else:
            self.logObject.log('Playing old video', 'INFO')
            expObj = edoExpect('omxplayer youtube.mp4', 3600, self.logObject)
            result = expObj.expect([pexpect.TIMEOUT, pexpect.EOF])

    class bgSyncClass(threading.Thread):
        def __init__(self, db, objSync, logObject):
            threading.Thread.__init__(self)
            self.logObject = logObject
            self.objDB = db
            self.counter = 0
            self.objSync = objSync

        def run(self):
            ''' Sync database to central repository '''
            if edoTestSocket(CHECK_IP, CHECK_PORT) == 0:
                print 'Start sync central database'
                self.objSyncDB = createSyncDB(SYNC_IP, SYNC_USER, SYNC_PASS, SYNC_DBNAME, self.logObject)
                self.objDB.sync(self.objSyncDB, self.objSync, 'cargps', 'sync', 'time', 'lat', 'lon', 'alt', 'speed', 'tripno', 'seq', 'dist')
                print 'Sync complete'
                return 0
            else:
                print 'No Connection, could not sync database'
                return 1


class MyApp(App):
    def build(self):
        sync_counter = ['None', 'False']
        # Create mainApp so DictProperty get created
        mainApp = rootWidget()
        # Schedule to run every interval
        Clock.schedule_interval(partial(mainApp.update, sync_counter), 10)
        Clock.schedule_interval(partial(mainApp.checkSyncYoutube, sync_counter), 10)
        return mainApp


if __name__ == '__main__':
    MyApp().run()
