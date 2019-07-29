import RPi.GPIO as GPIO
import time
import remotePiClasses.configClass as Config
import logging
logging.basicConfig(level=logging.INFO)

#GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BCM)

#Disable warnings
GPIO.setwarnings(False)
 
#Choice of PINS for ultrasonic
PIN_TRIGGER_FRONT = 9
PIN_ECHO_FRONT = 8

PIN_TRIGGER_REAR = 10
PIN_ECHO_REAR = 25

""" PIN_TRIGGER_FRONT_TOP = 23
PIN_ECHO_FRONT_TOP = 26 """

#Ultrasonic GPIO direction (IN / OUT)
GPIO.setup(PIN_TRIGGER_REAR, GPIO.OUT)
GPIO.setup(PIN_ECHO_REAR, GPIO.IN)

GPIO.setup(PIN_TRIGGER_FRONT, GPIO.OUT)
GPIO.setup(PIN_ECHO_FRONT, GPIO.IN)

""" GPIO.setup(PIN_TRIGGER_FRONT_TOP, GPIO.OUT)
GPIO.setup(PIN_ECHO_FRONT_TOP, GPIO.IN) """

def distanceRear():
    # set Trigger to HIGH
    GPIO.output(PIN_TRIGGER_REAR, True)
 
    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(PIN_TRIGGER_REAR, False)
 
    StartTime = time.time()
    StopTime = time.time()
 
    # save StartTime
    while GPIO.input(PIN_ECHO_REAR) == 0:
        StartTime = time.time()
 
    # save time of arrival
    while GPIO.input(PIN_ECHO_REAR) == 1:
        StopTime = time.time()
 
    # time difference between start and arrival
    TimeElapsed = StopTime - StartTime
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance = (TimeElapsed * 34300) / 2
 
    return distance


def distanceFront():
    # set Trigger to HIGH
    GPIO.output(PIN_TRIGGER_FRONT, True)
 
    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(PIN_TRIGGER_FRONT, False)
 
    StartTime = time.time()
    StopTime = time.time()
 
    # save StartTime
    while GPIO.input(PIN_ECHO_FRONT) == 0:
        StartTime = time.time()
 
    # save time of arrival
    while GPIO.input(PIN_ECHO_FRONT) == 1:
        StopTime = time.time()
 
    # time difference between start and arrival
    TimeElapsed = StopTime - StartTime
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance = (TimeElapsed * 34300) / 2
 
    return distance



""" def distanceFrontTop():
    # set Trigger to HIGH
    GPIO.output(PIN_TRIGGER_FRONT_TOP, True)
 
    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(PIN_TRIGGER_FRONT_TOP, False)
 
    StartTime = time.time()
    StopTime = time.time()
 
    # save StartTime
    while GPIO.input(PIN_ECHO_FRONT_TOP) == 0:
        StartTime = time.time()
 
    # save time of arrival
    while GPIO.input(PIN_ECHO_FRONT_TOP) == 1:
        StopTime = time.time()
 
    # time difference between start and arrival
    TimeElapsed = StopTime - StartTime
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance = (TimeElapsed * 34300) / 2
 
    return distance
 """
