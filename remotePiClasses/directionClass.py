import RPi.GPIO as GPIO
import remotePiClasses.configClass as Config
import logging
from remotePiClasses.bts7960_motor import BTS7960Motor
logging.basicConfig(level=logging.INFO)

#GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BCM)
 
#Disable warnings
GPIO.setwarnings(False)

#Choice of PINS for direction system
leftSidePin=24
leftSideForward=27
leftSideForwardReversePin=22
rightSidePin=23
rightSideForward=17
rightSideForwardReversePin=4

# The lowest frequence might be ideal to reduce consumption ?
# Not sure:  Generally 20kHz is a good choice for PWM frequency because it is well beyond of the dynamic range of motors and just beyond the range of human hearing
# http://hades.mech.northwestern.edu/index.php/Driving_a_high_current_DC_Motor_using_an_H-bridge
frequence=10 #in hz 
#frequence=20000 #in hz 

transitionSpeedIncrement = 1

#PWM dc_speeds
dc_stop = 0
dc_speed1 = 40
dc_speed2 = 45
dc_speed3 = 50
dc_speed4 = 75
dc_speed5 = 85
dc_speed6 = 100
""" dc_speed7 = 90
dc_speed8 = 95
dc_speed9 = 100 """

# Motor pin assignments (update as needed for your wiring)
LEFT_PWM_RIGHT = 24
LEFT_PWM_LEFT = 27
RIGHT_PWM_RIGHT = 23
RIGHT_PWM_LEFT = 17
PWM_FREQ = 1000

# Create motor instances
left_motor = BTS7960Motor(pwm_right_pin=LEFT_PWM_RIGHT, pwm_left_pin=LEFT_PWM_LEFT, freq_hz=PWM_FREQ)
right_motor = BTS7960Motor(pwm_right_pin=RIGHT_PWM_RIGHT, pwm_left_pin=RIGHT_PWM_LEFT, freq_hz=PWM_FREQ)

# Setup motors
left_motor.setup()
right_motor.setup()

# Remove all direct GPIO and PWM setup for motors below this point

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

   """    if power == "9":
      desiredSpeed = dc_speed9
   if power == "8":
      desiredSpeed = dc_speed8
   if power == "7":
      desiredSpeed = dc_speed7 """
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
   

# Power mapping: joystick value (string) to duty cycle (quadratic for finer low-speed control)
def map_power_to_duty(power):
    try:
        p = int(power)
        if p <= 0:
            return 0
        elif p >= 7:
            return 100
        else:
            return min(100, int((p/7)**2 * 100))
    except Exception:
        return 0


def set_speed_left(power, direction):
    if Config.DEBUG_ENABLED:
        logging.info('power left: %s', power)
    speed = map_power_to_duty(power)
    if direction == 'backward':
        speed = -speed
    left_motor.set_target_speed(speed)
    # left_motor.update_speed()  # Now handled by periodic update


def set_speed_right(power, direction):
    if Config.DEBUG_ENABLED:
        logging.info('power right: %s', power)
    speed = map_power_to_duty(power)
    if direction == 'backward':
        speed = -speed
    right_motor.set_target_speed(speed)
    # right_motor.update_speed()  # Now handled by periodic update


def left_side_forward(power):
    if Config.DEBUG_ENABLED:
        logging.info('left_side_forward')
    set_speed_left(power, 'forward')
    global currentDirectionLeftSide
    currentDirectionLeftSide = 'forward'
    clearSavedDirection()


def right_side_forward(power):
    if Config.DEBUG_ENABLED:
        logging.info('right_side_forward')
    set_speed_right(power, 'forward')
    global currentDirectionRightSide
    currentDirectionRightSide = 'forward'
    clearSavedDirection()


def left_side_backward(power):
    if Config.DEBUG_ENABLED:
        logging.info('left_side_backward')
    set_speed_left(power, 'backward')
    global currentDirectionLeftSide
    currentDirectionLeftSide = 'backward'
    clearSavedDirection()


def right_side_backward(power):
    if Config.DEBUG_ENABLED:
        logging.info('right_side_backward')
    set_speed_right(power, 'backward')
    global currentDirectionRightSide
    currentDirectionRightSide = 'backward'
    clearSavedDirection()


def stopLeft():
    if Config.DEBUG_ENABLED:
        logging.info('stopLeft')
    global currentDirectionLeftSide
    currentDirectionLeftSide = 'none'
    left_motor.stop()
    # No need to clear saved direction here


def stopRight():
    if Config.DEBUG_ENABLED:
        logging.info('stopRight')
    global currentDirectionRightSide
    currentDirectionRightSide = 'none'
    right_motor.stop()
    # No need to clear saved direction here

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
   
   
# Periodic update function for smooth acceleration

def update_motors_periodic():
    left_motor.update_speed()
    right_motor.update_speed()
   
   