echo "start GPS" | tee -a /home/pi/gps.log
sudo /etc/init.d/gpsd stop
sudo /etc/init.d/gpsd start

# Optionally if you like to play music in the background you could place a song edo.ogg in the directory and RPI uses omxplayer
#£ sh -c "while true ; do omxplayer ./edo.ogg ; done" &
echo "Set time, waiting for GPS to find location" | tee -a /home/pi/gps.log
python ./set_time.py 2>&1 | tee -a /home/pi/gps.log
echo "Start edoCarGps" | tee -a /home/pi/gps.log
python ./edoCarGps.py 2>&1 | tee -a /home/pi/gps.log
echo "Quit edoCarGps" | tee -a /home/pi/gps.log
