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

# The lowest frequence might be ideal to reduce consumption ?
# Not sure:  Generally 20kHz is a good choice for PWM frequency because it is well beyond of the dynamic range of motors and just beyond the range of human hearing
# http://hades.mech.northwestern.edu/index.php/Driving_a_high_current_DC_Motor_using_an_H-bridge
#frequence=10 #in hz 
frequence=20000 #in hz 

transitionSpeedIncrement = 1

#PWM dc_speeds
dc_stop = 0
dc_speed1 = 40
dc_speed2 = 45
dc_speed3 = 50
dc_speed4 = 75
dc_speed5 = 80
dc_speed6 = 85
dc_speed7 = 90
dc_speed8 = 95
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

transitionSpeedLeftSide = 0
transitionSpeedRightSide = 0

lastSavedDirectionLeftSide = 'none'
lastSavedDirectionRightSide = 'none'
lastSavedPowerLeftSide = 0
lastSavedPowerRightSide = 0

def getCurrentTransitionSpeedLeft():
   return transitionSpeedLeftSide

def getCurrentTransitionSpeedRight():
   return transitionSpeedRightSide

def get_transition_speed(side, power, direction):
   global transitionSpeedLeftSide
   global transitionSpeedRightSide

   global currentDirectionLeftSide
   transitionSpeed = 0

   if power == "9":
      desiredSpeed = dc_speed9
   if power == "8":
      desiredSpeed = dc_speed8
   if power == "7":
      desiredSpeed = dc_speed7
   if power == "6":
      desiredSpeed = dc_speed6
   if power == "5":
      desiredSpeed = dc_speed5
   if power == "4":
      desiredSpeed = dc_speed4
   if power == "3":
      desiredSpeed = dc_speed3
   if power == "2":
      desiredSpeed = dc_speed2
   if power == "1":
      desiredSpeed = dc_speed1
      
   # Same direction, then power motor with transition
   if direction == currentDirectionLeftSide:
      # If same power is desired by both side, set starting point at the currunt maximum of those two
      if currentPowerLeftSide == currentPowerRightSide:
         currentMaxTransitionSpeed = max(transitionSpeedLeftSide, transitionSpeedRightSide) # Hight speed side

         # Apply the offset bonus to righfull side
         if side == "left":
            transitionSpeed = transitionSpeedLeftSide = apply_transition_offset(currentMaxTransitionSpeed, desiredSpeed)
         elif side == "right":
            transitionSpeed = transitionSpeedRightSide = apply_transition_offset(currentMaxTransitionSpeed, desiredSpeed)
      else:
         # Apply the offset bonus to righfull side
         if side == "left":
            transitionSpeed = transitionSpeedLeftSide = apply_transition_offset(transitionSpeedLeftSide, desiredSpeed)
         elif side == "right":
            transitionSpeed = transitionSpeedRightSide = apply_transition_offset(transitionSpeedRightSide, desiredSpeed)

   # If there is a transition of direction, we reset the speed to the minimum and the transition will begin again
   else:
      # Reset speed of righfull side
      if side == "left":
         transitionSpeed = transitionSpeedLeftSide = dc_speed1
      elif side == "right":
         transitionSpeed = transitionSpeedRightSide = dc_speed1

   return transitionSpeed

def apply_transition_offset(curTransitionSpeed, desiredSpeed):
   if (curTransitionSpeed < desiredSpeed):
      return curTransitionSpeed + transitionSpeedIncrement
   else:
      return desiredSpeed
   

def set_speed_left(power, direction):
   if Config.DEBUG_ENABLED:
      logging.info('power left: %s', power)

   global currentPowerLeftSide
   currentPowerLeftSide = power

   transitionSpeed = get_transition_speed("left", power, direction)
   leftSide.start(transitionSpeed)


def set_speed_right(power, direction):
   if Config.DEBUG_ENABLED:
      logging.info('power right: %s', power)

   global currentPowerRightSide
   currentPowerRightSide = power

   transitionSpeed = get_transition_speed("right", power, direction)
   rightSide.start(transitionSpeed)


def left_side_forward(power):
    if Config.DEBUG_ENABLED:
      logging.info('left_side_forward')
    set_speed_left(power, 'forward')
    global currentDirectionLeftSide
    currentDirectionLeftSide = 'forward'
    GPIO.output(leftSideForward, 1)
    clearSavedDirection()

def right_side_forward(power):
    if Config.DEBUG_ENABLED:
      logging.info('right_side_forward')
    set_speed_right(power, 'forward')
    global currentDirectionRightSide
    currentDirectionRightSide = 'forward'
    GPIO.output(rightSideForward, 1)
    clearSavedDirection()

def left_side_backward(power):
    if Config.DEBUG_ENABLED:
      logging.info('left_side_backward')
    set_speed_left(power, 'backward')
    global currentDirectionLeftSide
    currentDirectionLeftSide = 'backward'
    GPIO.output(leftSideForward, 0)
    clearSavedDirection()

def right_side_backward(power):
    if Config.DEBUG_ENABLED:
      logging.info('right_side_backward')
    set_speed_right(power, 'backward')
    global currentDirectionRightSide
    currentDirectionRightSide = 'backward'
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
   
   