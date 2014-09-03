edoCarGps
==============

Background
--------------

This application was developed in Python 2.7 to fulfill the following

- Installed on Raspberry Pi connected to USB-GPS device
- Optionally connected to a monitorin using regular video-connection from RPI
- The speed, distance and statistics displayed graphically (using Kivy framework)
- Automatcially detects when home wireless-network in range and start syncronizing 
- Automatically download new random YouTube video when access to Internet [experimental]
- When driving slower than 10km/h for 5 minutes start playing downloaded YouTube-video [experimental]

----------------------
To-Do
----------------------

- View routes using web framework such as Web2Py

----------------------
Installation
----------------------

1) Make sure you have gpsd and required modules installed
	sudo apt-get install python gpsd gpsd-clients
2) Download required python script
	git clone https://github.com/engdan77/edocargps.git
3) Update options in configuration
	vi edoCarGps.py

----------------------
Command Line Arguments
----------------------

```
usage: ./edoCarGps.sh
```


-------------------------
Configuration
-------------------------

	SYNC_IP = 'ip_to_server'
	SYNC_USER = 'username_for_db'
	SYNC_PASS = 'pass_for_db'
	SYNC_DBNAME = 'cargps'
	YOUTUBE_URL = 'http://www.youtube.com/watch?v='
	YOUTUBE_ENABLE = False
	CHECK_IP = 'www.abc.se'
	CHECK_PORT = 80

-------------------------
Pictures
-------------------------
*Installation of Raspberry Pi in the car with USB-GPS and electrical switch component to turn on when car is*
![Main Board](https://github.com/engdan77/edocargps/blob/master/pics/img1.jpg)

*Monitor in car displaying the speed and distance each month*
![Main Board](https://github.com/engdan77/edocargps/blob/master/pics/img2.jpg)

