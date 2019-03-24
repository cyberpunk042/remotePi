import RPi.GPIO as GPIO

GREEN_LIGHT_PIN = 37
GPIO.setup(GREEN_LIGHT_PIN, GPIO.OUT)
GPIO.output(GREEN_LIGHT_PIN, 1) #Power led

BLUE_LIGHT_PIN = 38
GPIO.setup(BLUE_LIGHT_PIN, GPIO.OUT)


def turnOnBlueLed():
    GPIO.output(BLUE_LIGHT_PIN, 1) #Connection led

def turnOffBlueLed():
    GPIO.output(BLUE_LIGHT_PIN, 0) #Connection led