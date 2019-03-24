import RPi.GPIO as GPIO
import remotePiClasses.configClass as Config
import logging
logging.basicConfig(level=logging.INFO)

#GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BOARD)
 
#Disable warnings
GPIO.setwarnings(False)

#Choice of PINS for direction system
leftSidePin=16
leftSideForward=11
rightSidePin=18
rightSideForward=13

frequence=50 #in hz

#PWM dc_speeds
dc_stop = 0
dc_speed1 = 10
dc_speed2 = 25
dc_speed3 = 45
dc_speed4 = 65
dc_speed5 = 80
dc_speed7 = 90
dc_speed9 = 100
GPIO.setup(leftSidePin, GPIO.OUT)
leftSide = GPIO.PWM(leftSidePin, frequence)
GPIO.setup(leftSideForward, GPIO.OUT)

GPIO.setup(rightSidePin, GPIO.OUT)
rightSide = GPIO.PWM(rightSidePin, frequence)
GPIO.setup(rightSideForward, GPIO.OUT)

#Initial state
rightSide.stop()
GPIO.output(leftSideForward , 0)
leftSide.stop()
GPIO.output(rightSideForward, 0)

currentDirectionLeftSide = 'none'
currentDirectionRightSide = 'none'
currentPowerLeftSide = 0
currentPowerRightSide = 0

lastSavedDirectionLeftSide = 'none'
lastSavedDirectionRightSide = 'none'
lastSavedPowerLeftSide = 0
lastSavedPowerRightSide = 0


def set_speed_left(power):
    if Config.DEBUG_ENABLED:
      logging.info('power left: %s', power)
    if power == "9":
       leftSide.start(dc_speed9)
    if power == "7":
       leftSide.start(dc_speed7)
    if power == "5":
       leftSide.start(dc_speed5)
    if power == "4":
       leftSide.start(dc_speed4)
    if power == "3":
       leftSide.start(dc_speed3)
    if power == "2":
       leftSide.start(dc_speed2)
    if power == "1":
       leftSide.start(dc_speed1)
    global currentPowerLeftSide
    currentPowerLeftSide = power

def set_speed_right(power):
    if Config.DEBUG_ENABLED:
      logging.info('power right: %s', power)
    if power == "9":
       rightSide.start(dc_speed9)
    if power == "7":
       rightSide.start(dc_speed7)
    if power == "5":
       rightSide.start(dc_speed5)
    if power == "4":
       rightSide.start(dc_speed4)
    if power == "3":
       rightSide.start(dc_speed3)
    if power == "2":
       rightSide.start(dc_speed2)
    if power == "1":
       rightSide.start(dc_speed1)
    global currentPowerRightSide
    currentPowerRightSide = power

def left_side_forward(power):
    if Config.DEBUG_ENABLED:
      logging.info('left_side_forward')
    global currentDirectionLeftSide
    currentDirectionLeftSide = 'forward'
    set_speed_left(power)
    GPIO.output(leftSideForward, 1)
    clearSavedDirection()

def right_side_forward(power):
    if Config.DEBUG_ENABLED:
      logging.info('right_side_forward')
    global currentDirectionRightSide
    currentDirectionRightSide = 'forward'
    set_speed_right(power)
    GPIO.output(rightSideForward, 1)
    clearSavedDirection()

def left_side_backward(power):
    if Config.DEBUG_ENABLED:
      logging.info('left_side_backward')
    global currentDirectionLeftSide
    currentDirectionLeftSide = 'backward'
    set_speed_left(power)
    GPIO.output(leftSideForward, 0)
    clearSavedDirection()

def right_side_backward(power):
    if Config.DEBUG_ENABLED:
      logging.info('right_side_backward')
    global currentDirectionRightSide
    currentDirectionRightSide = 'backward'
    set_speed_right(power)
    GPIO.output(rightSideForward, 0)
    clearSavedDirection()

def stopLeft():
    if Config.DEBUG_ENABLED:
      logging.info('stopLeft')
    global currentDirectionLeftSide
    currentDirectionLeftSide = 'none'
    leftSide.stop()
    GPIO.output(leftSideForward , 0)
    # Since stop can be called by the poximity alert itself, it will not clear the saved direction

def stopRight():
    if Config.DEBUG_ENABLED:
      logging.info('stopRight')
    global currentDirectionRightSide
    currentDirectionRightSide = 'none'
    rightSide.stop()
    GPIO.output(rightSideForward, 0)
    # Since stop can be called by the poximity alert itself, it will not clear the saved direction

def saveDirection():
    global lastSavedDirectionLeftSide
    global lastSavedDirectionRightSide
    global lastSavedPowerLeftSide
    global lastSavedPowerRightSide
    lastSavedDirectionLeftSide = currentDirectionLeftSide
    lastSavedDirectionRightSide = currentDirectionRightSide
    lastSavedPowerLeftSide = currentPowerLeftSide
    lastSavedPowerRightSide = currentPowerRightSide

def clearSavedDirection():
   global lastSavedDirectionLeftSide
   global lastSavedDirectionRightSide
   
   lastSavedDirectionLeftSide = 'none'
   lastSavedDirectionRightSide = 'none'


def restoreDirection():
   global lastSavedDirectionLeftSide
   global lastSavedDirectionRightSide
   if Config.DEBUG_ENABLED:
      logging.info('restoreDirection')

   if lastSavedDirectionLeftSide == 'forward':
      left_side_forward(lastSavedPowerLeftSide)
      if Config.DEBUG_ENABLED:
         logging.info('restoreDirection left forward')
   elif lastSavedDirectionLeftSide == 'backward':
      left_side_backward(lastSavedPowerLeftSide)
      if Config.DEBUG_ENABLED:
         logging.info('restoreDirection left backward')

   if lastSavedDirectionRightSide == 'forward':
      right_side_forward(lastSavedPowerRightSide)
      if Config.DEBUG_ENABLED:
         logging.info('restoreDirection right backward')
   elif lastSavedDirectionRightSide == 'backward':
      right_side_backward(lastSavedPowerRightSide)
      if Config.DEBUG_ENABLED:
         logging.info('restoreDirection right backward')

   clearSavedDirection()
   
   