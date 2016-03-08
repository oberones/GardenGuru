#!/usr/bin/env python
#Shell interface for the GardenGuru project.

enable_camera = True
sensor_env_pin = 4
pump_pin = 23
script_home = '/opt/GardenGuru'
twitter_keys_file = '%s/twKeys' % (script_home)


####################################################################################################

import sys
import argparse
import datetime
import time
import Adafruit_DHT as sensor_env_api
import RPi.GPIO as GPIO
import picamera
from twython import Twython
import pymongo
from pymongo import MongoClient


#Twython vars
file = open(twitter_keys_file, 'r')
twCreds = file.readlines()
twitterApi = Twython(twCreds[0].rstrip(),twCreds[1].rstrip(),twCreds[2].rstrip(),twCreds[3].rstrip())

#piCamera vars
if enable_camera == True: 
    camera = picamera.PiCamera()

#GPIO vars
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

#pymongo vars
client = MongoClient()
db = client.planter
collection = db.env

#argparse vars
parser = argparse.ArgumentParser(description='Run GardenGuru from the shell')
parser.add_argument("-s", "--sensors", action="store_true", help="Check environment sensor readings")
parser.add_argument("-t", "--tweet", action="store_true", help="Tweet the sensor results")
parser.add_argument("-d", "--store", action="store_true", help="Store sensor results in the database")
parser.add_argument("-m", "--message", type=str, help="Send a twitter message as GardenGuru")

args = parser.parse_args()

class EST(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(hours=-5)

    def dst(self, dt):
        return datetime.timedelta(0)
now = datetime.datetime.now(EST())
datestamp = now.strftime("%m-%d-%Y")
timestamp = now.strftime("%H:%M:%S")



def menu_main():       
    print 15 * "-" , "MAIN" , 15 * "-"
    print "1. Check Sensors"
    print "2. Power Cycle the pump"
    print "3. Tweet a Message"
    print "4. Job Scheduler"
    print "5. Exit Garden Guru"
    print 34 * "-"

def menu_sensor(hum, temp):
    print
    print 13 * "=" , "SENSORS" , 13 * "="
    print "Temperature: %d F" % temp
    print "Humidity: %d%%" % hum
    print 34 * "." 
    print "1. Update Readings"
    print "2. Main Menu"
    print 34 * "="
    
def menu_power(state):
    print
    print 15 * "=" , "POWER" , 14 * "="
    if state == 0:
        print "Pump is currently OFF"
        print 15 * "=" , "POWER" , 14 * "="
        print "1. Power ON the Pump"
    elif state == 1:
        print "Pump is currently ON" 
        print "1. Power OFF the Pump"
    else:
        print "Pump state unknown! (%s)" (state)
    print "2. Main Menu"
    print 34 * "="

   
def get_env():
    humidity, temperature = sensor_env_api.read_retry(sensor_env_api.DHT11, sensor_env_pin)
    temperature = temperature * 9/5.0 + 32    #Convert C to F
    humidity = 100 - humidity    #Convert dryness to moisture
    return (humidity, temperature)
    
def write_env(hum, temp):
    record = {"date": datestamp, "timestamp": timestamp, "temperature": temp, "humidity": hum}
    collection.insert(record)

def publish_tweet(message, pic):
    if len(message) <= 140:
        if pic == True:
            camera.capture('current.jpg')
            photo = open('./current.jpg', 'rb')
            response = twitterApi.upload_media(media=photo)
            twitterApi.update_status(status=message, media_ids=[response['media_id']])
        elif pic == False:
            twitterApi.update_status(status=message)
	else:
	    print "Invalid message length."
        


if args.sensors:
    hum, temp = get_env()
    print "Temperature: %d F" % (temp)
    print "Humidity: %d%%" % (hum)
    if args.tweet:
        message = "%s - It's currently %d F in my garden and the humidity is %d%%." % (timestamp, temp, hum)
        publish_tweet(message, False)
    if args.store:
        write_env(hum, temp)
elif args.message:
    publish_tweet(args.message, False)	

else:              
    loopMain=True      
    while loopMain:          
        menu_main()   
        choice = raw_input("Enter your choice [1-5]: ")
     
        if choice=="1":
            loopSub=True
            while loopSub: 
                hum, temp = get_env()
                if humidity is not None and temperature is not None:
                    menu_sensor(hum, temp)	
                    choice_sensor = raw_input("Select an option [1-2]: ")
	            if choice_sensor=="1":
                        next
                    elif choice_sensor=="2":
	                loopSub=False 
                    else:
                        print "Invalid option." 
                else:
                    print "ERROR: Unable to read sensor."
            

        elif choice=="2":
            loopSub=True
            GPIO.setup(pump_pin, GPIO.OUT)
            while loopSub:
                powerState=GPIO.raw_input(pump_pin)
                menu_power(powerState)
                choice_power = raw_input("Select an option [1-2]: ")
                if choice_power=="1" and powerState=="0":
                    duration = input("How many minutes? [1-30]") 
                    if not duration < 1 or duration > 30:  
                        GPIO.output(pump_pin, True)
                        print "Powering the pump ON for %d minutes" % (duration)
                        sleep(duration*60)
                        GPIO.output(pump_pin, False)
                    else:
                        print "Invalid option." 
                elif choice_power=="1" and powerState=="1":
                    GPIO.output(pump_pin, False)
                    print "Powering the pump OFF"
                elif choice_power=="2":
                    GPIO.cleanup()
                    loopSub=False
                else:
                    print "Invalid option."

        elif choice=="3":
            loopSub=True
            while loopSub:
                message = raw_input("Message: ")
                if len(message) <= 140:
		    if enable_camera == True:
                        loopSubSub=True
                        while loopSubSub:
                            choice_pic = raw_input("Include a picture [y/n]: ")
                            if choice_pic == "y":
                                publish_tweet(message, True)
                                loopSubSub=False
                            elif choice_pic == "n":
                                publish_tweet(message, False)
                                loopSubSub=False
                            else:
                                print "Invalid option."
                        loopSub=False
                else:
                    print "Invalid message length."

        elif choice=="4":
	    print "Coming soon!"

        elif choice=="5":
            print "Goodbye!"
            loopMain=False 

        else:
            print "Invalid option. Enter any key to try again.."
