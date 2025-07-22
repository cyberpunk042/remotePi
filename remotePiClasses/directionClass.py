import RPi.GPIO as GPIO
import remotePiClasses.configClass as Config
import logging
from remotePiClasses.bts7960_motor import BTS7960Motor
logging.basicConfig(level=logging.INFO)

#GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BCM)
 
#Disable warnings
GPIO.setwarnings(False)

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

# Power mapping: joystick value (float or string) in [-1, 1] to duty cycle [-100, 100]
def map_power_to_duty(power):
    try:
        p = float(power)
        p = max(-1.0, min(1.0, p))  # Clamp to [-1, 1]
        return int(p * 100)
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


# Periodic update function for smooth acceleration
def update_motors_periodic():
    left_motor.update_speed()
    right_motor.update_speed()
   
   